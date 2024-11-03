# -*- coding: utf-8 -*-

from odoo import http
from odoo.addons.web.controllers.main import Database, Home
from odoo.http import request


class WebDatabase(Database):

    def _is_redirect_emenu(self):
        hostname = request.env["ir.config_parameter"].sudo().get_param('base_setup.pos_emenu_domain')
        if hostname:
            hostname = hostname.strip()
            hostname = hostname.replace('http://','').replace('https://','')
            hostname = hostname.replace('www.', '') # May replace some false positives ('www.com')
            hostname = hostname.split('/')
            if hostname:
                hostname = hostname[0]
            if hostname in request.httprequest.host:
                return True
        return False

    @http.route('/web/database/manager', type='http', auth="none")
    def manager(self, **kw):
        res = super(WebDatabase,self).manager(**kw)    

        #TODO: IF domain is set for E-menu then cannot access this route
        if self._is_redirect_emenu():
            return http.local_redirect('/emenu-404')

        return res

    @http.route('/web/database/selector', type='http', auth="none")
    def selector(self, **kw):
        res = super(WebDatabase,self).selector(**kw)

        #TODO: IF domain is set for E-menu then cannot access this route
        if self._is_redirect_emenu():
            return http.local_redirect('/emenu-404')

        return res

class WebHome(Home):

    def _is_redirect_emenu(self):
        hostname = request.env["ir.config_parameter"].sudo().get_param('base_setup.pos_emenu_domain')
        if hostname:
            hostname = hostname.strip()
            hostname = hostname.replace('http://','').replace('https://','')
            hostname = hostname.replace('www.', '') # May replace some false positives ('www.com')
            hostname = hostname.split('/')
            if hostname:
                hostname = hostname[0]
            if hostname in request.httprequest.host:
                return True
        return False

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        #TODO: IF domain is set for E-menu then cannot access this route
        if self._is_redirect_emenu():
            return http.local_redirect('/emenu-404')

        return super(WebHome, self).web_client(s_action, **kw)

#     @http.route('/web/login', type='http', auth="none")
#     def web_login(self, redirect=None, **kw):
#         res = super(WebHome,self).web_login(redirect=None, **kw)
        
#         #TODO: IF domain is set for E-menu then cannot access this route
#         if self._is_redirect_emenu():
#             return http.local_redirect('/emenu-404')
        
#         return res
