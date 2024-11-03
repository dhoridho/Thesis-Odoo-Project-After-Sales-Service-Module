# -*- coding: utf-8 -*-

import odoo
import odoo.modules.registry
from odoo.tools.translate import _
from odoo.exceptions import AccessError
from odoo.addons.web.controllers.main import ensure_db, Home
from odoo.http import Root, Response
from odoo.modules import get_resource_path
from odoo.tools.mimetypes import guess_mimetype
from odoo import http
from odoo.http import request
from odoo.service import security

import json
import base64
import functools
import io
import os
import logging

_logger = logging.getLogger(__name__)

BASE_PATH = os.path.dirname(os.path.dirname(__file__))
db_monodb = http.db_monodb


class Home(odoo.addons.web.controllers.main.Home):
    '''
    inhere home to extend web.login style
    '''

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        '''
        rewrtie the login go support login style
        :param redirect:
        :param kw:
        :return:
        '''
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            try:
                uid = request.session.authenticate(
                    request.session.db, request.params['login'], request.params['password'])
                request.params['login_success'] = True
                return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                request.uid = old_uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employees can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        # get the extra style data
        user_setting = request.env["awesome_theme_pro.theme_setting_manager"].sudo().get_user_setting(
            get_mode_data=False, get_style_txt=False)
        cur_style_id = user_setting["cur_style_id"]
        login_style = user_setting["settings"]["login_style"] or "login_style1"
        login_template = 'awesome_theme_pro.{login_style}'.format(login_style=login_style)
        style_txt = request.env["awesome_theme_pro.style_item"].get_login_style_data(cur_style_id, login_style)
        values['login_style_txt'] = style_txt
        values['title'] = user_setting.get("window_default_title", "Awesome Odoo")
        values['powered_by'] = user_setting.get("powered_by", "Awesome Odoo")

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        response = request.render(login_template, values)

        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @http.route('/awesome_theme_pro/export_theme_style/<int:style_id>', type='http', auth="user")
    def export_theme_style(self, style_id):
        '''
        export style data
        :param style_id:
        :return:
        '''
        theme_style = request.env["awesome_theme_pro.theme_style"].sudo().browse(style_id)
        data = theme_style.with_context(export_style=True).get_styles()
        return request.make_response(
            data=json.dumps(data[0]), headers=[('Content-Type', 'application/json')])

    @http.route([
        '/web/binary/company_small_logo',
        '/small_logo',
        '/small_logo.png',
    ], type='http', auth="none", cors="*")
    def company_small_logo(self, dbname=None, **kw):
        '''
        get the small logo
        :param dbname:
        :param kw:
        :return:
        '''
        imgname = 'res_company_small_logo'
        imgext = '.png'
        placeholder = functools.partial(
            get_resource_path, 'awesome_theme_pro', 'static', 'images')
        uid = None
        if request.session.db:
            dbname = request.session.db
            uid = request.session.uid
        elif dbname is None:
            dbname = db_monodb()

        if not uid:
            uid = odoo.SUPERUSER_ID

        if not dbname:
            response = http.send_file(placeholder(imgname + imgext))
        else:
            try:
                # create an empty registry
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    company = int(kw['company']) if kw and kw.get('company') else False
                    if company:
                        cr.execute("""SELECT logo_small, write_date
                                        FROM res_company
                                       WHERE id = %s
                                   """, (company,))
                    else:
                        cr.execute("""SELECT c.logo_small, c.write_date
                                        FROM res_users u
                                   LEFT JOIN res_company c
                                          ON c.id = u.company_id
                                       WHERE u.id = %s
                                   """, (uid,))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_base64 = base64.b64decode(row[0])
                        image_data = io.BytesIO(image_base64)
                        mimetype = guess_mimetype(image_base64, default='image/png')
                        imgext = '.' + mimetype.split('/')[1]
                        if imgext == '.svg+xml':
                            imgext = '.svg'
                        response = http.send_file(
                            image_data, filename=imgname + imgext, mimetype=mimetype, mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception as error:
                response = http.send_file(placeholder(imgname + imgext))

        return response

    @http.route('/awesome_theme_pro/get_theme_modes_data', type='http', auth="user")
    def get_theme_modes_data(self):
        '''
        export style data
        :param style_id:
        :return:
        '''
        result = ""
        theme_modes = request.env["awesome_theme_pro.theme_mode"].sudo().browse()
        for theme_mode in theme_modes:
            # ignore normal mode
            if theme_mode.name == "normal":
                continue
            result += "\\ mode " + theme_mode.name + "\n" + theme_mode.compiled_mode_style_css
        return request.make_response(
            data=result,
            headers=[('Content-Type', 'text/css')])
