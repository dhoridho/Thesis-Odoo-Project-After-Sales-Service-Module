# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.web.controllers.main import Home as web_Home, ensure_db
from odoo.http import content_disposition, dispatch_rpc, request
import werkzeug
import werkzeug.utils
import urllib.parse

class web_Home(web_Home):
    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        ensure_db()
        if not request.session.uid:
            redirect = ''
            if kw.get('redirect'):
                redirect = kw.get('redirect')
                redirect = '?redirect='+urllib.parse.quote(redirect, safe='')
            return werkzeug.utils.redirect('/web/login'+redirect, 303)
        return super(web_Home, self).web_client(s_action, **kw)
