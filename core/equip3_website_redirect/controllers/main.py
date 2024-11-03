from odoo import http, tools
from odoo.http import request


class Home(http.Controller):    
    @http.route('/', type='http', auth="none")
    def index(self, s_action=None, db=None, **kw):
        return http.local_redirect('/web', query=request.params, keep_hash=True)


    @http.route('/shop', type='http', auth="none")
    def shop(self, s_action=None, db=None, **kw):
        return http.local_redirect('/web', query=request.params, keep_hash=True)