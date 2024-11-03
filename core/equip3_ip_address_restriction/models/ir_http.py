# Import necessary modules
import logging
from datetime import datetime, timedelta
from odoo import models, http, SUPERUSER_ID
from odoo.exceptions import AccessDenied
import time
import werkzeug
import werkzeug.exceptions
from odoo.http import request
from psycopg2 import OperationalError
# Custom RetryableError class
class RetryableError(Exception):
    pass

# Logger setup
_logger = logging.getLogger(__name__)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    # Utility function to update user session
    @classmethod
    def _update_user(cls, sid, uid, should_be_logged_out):
        """ Function for updating session details for the corresponding user """
        if uid and sid :
            # now_str = now.strftime('%Y-%m-%d %H:%M:%S')
            # exp_date_str = exp_date.strftime('%Y-%m-%d %H:%M:%S')
            query = """
                UPDATE res_users
                SET sid = %s, logged_in = 'True'
                WHERE id = %s
            """
            params = (sid,  uid)
            for attempt in range(2):
                try:
                    request.env.cr.execute(query, params)
                    break
                except OperationalError as e:
                    request.env.cr.rollback() 
                    if 'could not serialize access due to concurrent update' in str(e):
                        if attempt < 2:  # Wait a bit and retry
                            time.sleep(0.5)
                            continue
                    _logger.error('Error executing SQL query: %s', e)

    @classmethod
    def _authenticate(cls, auth_method='user'):
        try:
            if request.session.uid:
                uid = request.session.uid
                user_pool = request.env['res.users'].with_user(SUPERUSER_ID).browse(uid)

                sid = request.session.sid
                last_update = user_pool.last_update
                should_be_logged_out = user_pool.should_be_logged_out
                now = datetime.now()
                exp_date = datetime.now() + timedelta(minutes=45)

                # if uid and user_pool.sid and sid != user_pool.sid:
                #     # Retryable update user session
                #     cls._update_user(sid, uid, should_be_logged_out)
                # Retryable update user session
                cls._update_user(sid, uid, should_be_logged_out)

        except RetryableError as re:
            _logger.info("Retryable error during updating user session...%s", re)
            pass

        try:
            if request.session.uid:
                try:
                    request.session.check_security()
                    # what if error in security.check()
                    #   -> res_users.check()
                    #   -> res_users._check_credentials()
                except (AccessDenied, http.SessionExpiredException):
                    # All other exceptions mean undetermined status (e.g. connection pool full),
                    # let them bubble up
                    request.session.logout(keep_db=True)

            if request.uid is None:
                method = "_auth_method_%s" % auth_method.routing['auth']
                getattr(cls, method)()

        except (AccessDenied, http.SessionExpiredException, werkzeug.exceptions.HTTPException):
            raise
        except Exception:
            _logger.info("Exception during request Authentication.", exc_info=True)
            raise AccessDenied()

        return auth_method
