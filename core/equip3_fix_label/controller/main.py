from odoo import http
from odoo.http import request
from odoo.service import security
from odoo.addons.web.controllers.main import Home

class ClearCache(Home):

    @http.route('/web/clear_cache/<int:user_id>', type='http', auth='user', sitemap=False)
    def clear_cache(self, user_id, **kwargs):  # @UnusedVariable
        uid = request.env.user.id  # @UndefinedVariable
        if request.env.user._is_system():  # @UndefinedVariable
            request.session.impersonate_uid = uid
            uid = request.session.uid = user_id
            request.env['res.users'].clear_caches()

        return http.local_redirect(self._login_redirect(uid), keep_hash=True)
