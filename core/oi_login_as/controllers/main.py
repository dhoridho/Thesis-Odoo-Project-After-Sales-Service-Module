# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.service import security
from odoo.addons.web.controllers.main import Home

class LoginAs(Home):
    
    @http.route('/web/login_as/<int:user_id>', type='http', auth='user', sitemap=False)
    def switch_to_user(self, user_id, **kwargs):  # @UnusedVariable
        uid = request.env.user.id  # @UndefinedVariable
        if request.env.user._is_system():  # @UndefinedVariable
            request.session.impersonate_uid = uid
            uid = request.session.uid = user_id
            request.env['res.users'].clear_caches()
            request.session.session_token = security.compute_session_token(request.session, request.env)

        return http.local_redirect(self._login_redirect(uid), keep_hash=True)

    @http.route('/web/login_back', type='http', auth='user', sitemap=False)
    def switch_back(self, **kwargs):  # @UnusedVariable
        uid = request.env.user.id  # @UndefinedVariable
        if request.session.impersonate_uid:  # @UndefinedVariable
            uid = request.session.uid = request.session.impersonate_uid  # @UndefinedVariable
            request.session.impersonate_uid = False
            request.env['res.users'].clear_caches()
            request.session.session_token = security.compute_session_token(request.session, request.env)                        

        return http.local_redirect(self._login_redirect(uid), query={'debug':1}, keep_hash=True)
