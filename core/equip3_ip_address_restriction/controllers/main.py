import os
import werkzeug
from odoo.addons.web.controllers import main
from odoo.http import request
from odoo.exceptions import Warning
import odoo
from odoo import SUPERUSER_ID
import odoo.modules.registry
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import http
from odoo import fields
from datetime import datetime, timedelta
import werkzeug
import pytz
import logging
_logger = logging.getLogger(__name__)


def clear_session_history(u_sid, f_uid=False):
    """ Clear all the user session histories for a particular user """
    path = odoo.tools.config.session_dir
    store = werkzeug.contrib.sessions.FilesystemSessionStore(
        path, session_class=odoo.http.OpenERPSession, renew_missing=True)
    session_fname = store.get_session_filename(u_sid)
    try:
        os.remove(session_fname)
        return True
    except OSError:
        pass
    return False 


def super_clear_all():
    """ Clear all the user session histories """
    path = odoo.tools.config.session_dir
    store = werkzeug.contrib.sessions.FilesystemSessionStore(
        path, session_class=odoo.http.OpenERPSession, renew_missing=True)
    for fname in os.listdir(store.path):
        path = os.path.join(store.path, fname)
        try:
            os.unlink(path)
        except OSError:
            pass
    return True


class Session(main.Session):
    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/web'):
        user = request.env['res.users'].with_user(1).search(
            [('id', '=', request.session.uid)])
        # clear user session
        user._clear_session()
        request.session.logout(keep_db=True)
        return werkzeug.utils.redirect(redirect, 303)

    @http.route('/clear_all_sessions', type='http', auth="none")
    def logout_all(self, redirect='/web', f_uid=False):
        """ Log out from all the sessions of the current user """
        if f_uid:
            user = request.env['res.users'].with_user(1).browse(int(f_uid))
            if user:
                # clear session session file for the user
                session_cleared = clear_session_history(user.sid, f_uid)
                if session_cleared:
                    # clear user session
                    user._clear_session()
        request.session.logout(keep_db=True)
        return werkzeug.utils.redirect(redirect, 303)

    @http.route('/super/logout_all', type='http', auth="none")
    def super_logout_all(self, redirect='/web'):
        """ Log out from all the sessions of all the users """
        users = request.env['res.users'].with_user(1).search([])
        for user in users:
            # clear session session file for the user
            session_cleared = super_clear_all()
            if session_cleared:
                # clear user session
                user._clear_session()
        request.session.logout(keep_db=True)
        return werkzeug.utils.redirect(redirect, 303)
    
class LogoutController(http.Controller):
    @http.route('/should_logout', type='json', auth='user')
    def should_logout(self):
        return request.env.user.should_be_logged_out


class Home(main.Home):
    @http.route('/web/login', type='http', auth="public")
    def web_login(self, redirect=None, **kw):
        # main.ensure_db()
        res = super(Home, self).web_login(redirect=redirect, **kw)
        request.params['login_success'] = False

        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID
        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None
        if request.httprequest.method == 'POST':
            old_uid = request.uid
            sid = request.httprequest.session.sid
            current_ip = request.httprequest.remote_addr
            public_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.httprequest.remote_addr
            last_time_login = datetime.now()
            user_rec = request.env['res.users'].sudo().search([('login', '=', request.params['login'])])
            if not user_rec:
                user_rec = request.env['res.users'].sudo().search([('login', '=', request.params['login']),('active','=',False)])

            if user_rec.ip_address_login_toggle == True:
                user_rec.active = True
                ip_address_list = []
                for rec in user_rec.ip_address_ids:
                    ip_address_list.append(rec.ip_address)

                if len(ip_address_list) == 0:
                    try:
                        with request.env.cr.savepoint():
                            uid = request.session.authenticate(
                                    request.session.db,
                                    request.params['login'],
                                    request.params['password'])
                        request.params['login_success'] = True
                        # vals = {
                        #     'ip_address': current_ip,
                        #     'user_id': user_rec.id,
                        #     'state': 'success',
                        #     'time_login': fields.Datetime.now()
                        # }
                        # request.env['log.login'].sudo().create(vals)
                        query = """
                            INSERT INTO log_login (ip_address, user_id, state, time_login,create_date,create_uid,write_date,write_uid)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        params = (
                                    current_ip,
                                    user_rec.id,
                                    'success',
                                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    user_rec.id,
                                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    user_rec.id
                                )
                        request.env.cr.execute(query, params)
                        user_rec.write({'sid': sid,
                                        'last_login': last_time_login,
                                        'logged_in': True,
                                        'should_be_logged_out': False,
                                        'current_ip_address': current_ip,
                                        'ip_address_after_login': current_ip})
                        # return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
                    except odoo.exceptions.AccessDenied as e:
                        request.uid = old_uid
                        if e.args == odoo.exceptions.AccessDenied().args:
                            values['error'] = _("Wrong login/password")
                        else:
                            values['error'] = e.args[0]
                
                else:
                    
                    if current_ip in ip_address_list:
                        if user_rec.time_restricted == True:
                            day_restricted_list = []
                            day_restricted = request.env['day.restricted'].sudo().search([('res_user_id', '=', user_rec.id)])
                            for rec in day_restricted:
                                day_restricted_list.append(rec.day)

                            user_tz = user_rec.tz or 'UTC'
                            local = pytz.timezone(user_tz)
                            current_day = datetime.strftime(pytz.utc.localize(datetime.now()).astimezone(local), "%A")
                            current_hour = datetime.strftime(pytz.utc.localize(datetime.now()).astimezone(local), "%H.%M")
                            current_time = datetime.strptime(current_hour, "%H.%M")
                            formatted_time = current_time.replace(second=0).strftime("%H:%M:%S")
                            current_time = datetime.strptime(formatted_time, "%H:%M:%S")
                            current_datetime = datetime.utcnow()

                            end_timedelta = None

                            if current_day in day_restricted_list:
                                for rec in day_restricted:
                                    if rec.day == current_day:
                                        # Assuming start_time and end_time are in the format 'HH.MM'

                                        start_time = rec.start_time
                                        hour_start = int(start_time)
                                        minute_start = int((start_time - hour_start) * 60)
                                        start_timedelta = timedelta(hours=hour_start, minutes=minute_start)

                                        end_time = rec.end_time
                                        hour_end = int(end_time)
                                        minute_end = int((end_time - hour_end) * 60)
                                        end_timedelta = timedelta(hours=hour_end, minutes=minute_end)
                                        
                                        start_time = datetime.strptime(str(start_timedelta), "%H:%M:%S")
                                        end_time = datetime.strptime(str(end_timedelta), "%H:%M:%S")

                                        if end_timedelta is None:
                                            end_timedelta = timedelta(minutes=45)

                                        exp_date = datetime(current_datetime.year, 1, 1) + end_timedelta

                                        if not start_time <= current_time <= end_time:
                                            request.uid = old_uid
                                            values['error'] = _("Not allowed to login at this time, please contact administrator!")
                                            response = request.render('web.login', values)
                                            response.headers['X-Frame-Options'] = 'DENY'
                                            request.session.logout(keep_db=True)
                                            return response
                                        else:
                                            try:
                                                with request.env.cr.savepoint():
                                                    uid = request.session.authenticate(
                                                            request.session.db,
                                                            request.params['login'],
                                                            request.params['password'])
                                                request.params['login_success'] = True
                                                # vals = {
                                                #     'ip_address': current_ip,
                                                #     'user_id': user_rec.id,
                                                #     'state': 'success',
                                                #     'time_login': fields.Datetime.now()
                                                # }
                                                # request.env['log.login'].sudo().create(vals)
                                                query = """
                                                    INSERT INTO log_login (ip_address, user_id, state, time_login,create_date,create_uid,write_date,write_uid)
                                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                                """
                                                params = (
                                                    current_ip,
                                                    user_rec.id,
                                                    'success',
                                                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                                    user_rec.id,
                                                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                                    user_rec.id
                                                )
                                                request.env.cr.execute(query, params)
                                                user_rec.write({'sid': sid,
                                                                'exp_date': exp_date,
                                                                'last_login': last_time_login,
                                                                'logged_in': True,
                                                                'should_be_logged_out': False,
                                                                'current_ip_address': current_ip,
                                                                'ip_address_after_login': current_ip})
                                                # return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
                                            except odoo.exceptions.AccessDenied as e:
                                                request.uid = old_uid
                                                if e.args == odoo.exceptions.AccessDenied().args:
                                                    values['error'] = _("Wrong login/password")
                                                else:
                                                    values['error'] = e.args[0]
                            else:
                                request.uid = old_uid
                                values['error'] = _("Not allowed to login at this day, please contact administrator!")
                                response = request.render('web.login', values)
                                response.headers['X-Frame-Options'] = 'DENY'
                                request.session.logout(keep_db=True)
                                return response

                        else:
                            try:
                                with request.env.cr.savepoint():
                                    uid = request.session.authenticate(
                                            request.session.db,
                                            request.params['login'],
                                            request.params['password'])
                                request.params['login_success'] = True
                                query = """
                                    INSERT INTO log_login (ip_address, user_id, state, time_login,create_date,create_uid,write_date,write_uid)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                """
                                params = (
                                    current_ip,
                                    user_rec.id,
                                    'success',
                                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    user_rec.id,
                                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    user_rec.id
                                )
                                request.env.cr.execute(query, params)
                                user_rec.write({'sid': sid,
                                                'last_login': last_time_login,
                                                'logged_in': True,
                                                'should_be_logged_out': False,
                                                'current_ip_address': current_ip,
                                                'ip_address_after_login': current_ip})
                                # return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
                            except odoo.exceptions.AccessDenied as e:
                                request.uid = old_uid
                                if e.args == odoo.exceptions.AccessDenied().args:
                                    values['error'] = _("Wrong login/password")
                                else:
                                    values['error'] = e.args[0]

                    else:
                        request.uid = old_uid
                        values['error'] = _("Your Ip Address %s is not allowed to login, please contact administrator!" % current_ip)
                        response = request.render('web.login', values)
                        response.headers['X-Frame-Options'] = 'DENY'
                        request.session.logout(keep_db=True)
                        return response
            else:
                try:
                    with request.env.cr.savepoint():
                        uid = request.session.authenticate(
                                request.session.db,
                                request.params['login'],
                                request.params['password'])
                    request.params['login_success'] = True
                    # vals = {
                    #     'ip_address': current_ip,
                    #     'user_id': user_rec.id,
                    #     'state': 'success',
                    #     'time_login': fields.Datetime.now()
                    # }
                    # request.env['log.login'].sudo().create(vals)
                    query = """
                            INSERT INTO log_login (ip_address, user_id, state, time_login,create_date,create_uid,write_date,write_uid)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                    params = (
                                current_ip,
                                user_rec.id,
                                'success',
                                datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                user_rec.id,
                                datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                user_rec.id
                            )
                    request.env.cr.execute(query, params)
                    user_rec.write({'sid': sid,
                                    'last_login': last_time_login,
                                    'logged_in': True,
                                    'should_be_logged_out': False,
                                    'current_ip_address': current_ip,
                                    'ip_address_after_login': current_ip})
                    # return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
                except odoo.exceptions.AccessDenied as e:
                    request.uid = old_uid
                    if e.args == odoo.exceptions.AccessDenied().args:
                        values['error'] = _("Wrong login/password")
                    else:
                        values['error'] = e.args[0]
        return res