from odoo import http
from odoo.http import request
# from threading import Lock

# class UserController(http.Controller):
#     _locks = {}

#     @http.route('/update_ip', type='json', auth='user')
#     def update_ip(self, ip):
#         user_id = request.uid
#         if user_id not in self._locks:
#             self._locks[user_id] = Lock()

#         with self._locks[user_id]:
#             user = request.env['res.users'].sudo().browse(user_id)
#             user.write({'ip_address_after_login': ip})

class CheckIpController(http.Controller):
    @http.route('/update_ip', type='json', auth='user')
    def update_ip(self, ip):
        ip_local = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.httprequest.remote_addr
        user = request.env['res.users'].sudo().browse(request.uid)
        user.write({'ip_address_after_login': ip})