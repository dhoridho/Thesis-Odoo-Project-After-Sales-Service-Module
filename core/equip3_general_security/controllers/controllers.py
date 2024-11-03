# -*- coding: utf-8 -*-
# from odoo import http
from odoo.addons.website.controllers.main import Website
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request,route
from odoo import http,_
import logging
from odoo.exceptions import UserError
import werkzeug

from odoo.addons.auth_signup.models.res_users import SignupError
_logger = logging.getLogger(__name__)







class AuthSignupHomeInherit(AuthSignupHome):
    
    @http.route('/web/reset_password', type='http', auth='public', website=True, sitemap=False)
    def web_auth_reset_password(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()
        print("already hereee")

        if not qcontext.get('token') and not qcontext.get('reset_password_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                if qcontext.get('token'):
                    self.do_signup(qcontext)
                    return self.web_login(*args, **kw)
                else:
                    login = qcontext.get('login')
                    assert login, _("No login provided.")
                    _logger.info(
                        "Password reset attempt for <%s> by user <%s> from %s",
                        login, request.env.user.login, request.httprequest.remote_addr)
                    request.env['res.users'].sudo().reset_password(login)
                    qcontext['message'] = _("Password reset is sent to email if user exists")
            except UserError as e:
                qcontext['error'] = e.args[0]
            except SignupError:
                qcontext['error'] = _("Could not reset your password")
                _logger.exception('error when resetting password')
            except Exception as e:
                qcontext['message'] = _("Password reset is sent to email if user exists")
                response = request.render('auth_signup.reset_password', qcontext)
                response.headers['X-Frame-Options'] = 'DENY'


        response = request.render('auth_signup.reset_password', qcontext)
        response.headers['X-Frame-Options'] = 'DENY'
        return response
    
class Website(Website):
    @route('/website/info', type='http', auth="public", website=True, sitemap=True)
    def website_info(self, **kwargs):
        return request.render('website.page_404', None)


    # will make site cannot be indexing on google
    @http.route(['/robots.txt'], type='http', auth="public", website=True, sitemap=False)
    def robots(self, **kwargs):
        return request.render('website.page_404', None)


    @http.route('/sitemap.xml', type='http', auth="public", website=True, multilang=False, sitemap=False)
    def sitemap_xml_index(self, **kwargs):
        return request.render('website.page_404', None)

    @http.route('/website/snippet/filters', type='json', auth='public', website=True)
    def get_dynamic_filter(self, filter_id, template_key, limit=None, search_domain=None):
        return request.render('website.page_404', None)


    @http.route('/website/snippet/filter_templates', type='json', auth='public', website=True)
    def get_dynamic_snippet_templates(self, filter_id=False):
        return request.render('website.page_404', None)


    
    

    
    
