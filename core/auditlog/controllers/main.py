from odoo.addons.web.controllers import main
from odoo.http import request
import odoo
import odoo.modules.registry
from odoo.tools.translate import _
from odoo import http


class UserLog(http.Controller):

    @http.route('/get_remote_ip', type='http', auth="user")
    def get_remote_ip(self):
        # Get the remote IP address from the request object
        remote_ip = request.httprequest.environ.get('REMOTE_ADDR')
        request.session['remote_ip'] = remote_ip
        return remote_ip

   





