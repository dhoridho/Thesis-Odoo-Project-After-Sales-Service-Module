# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class Equip3PrivyIntegration(http.Controller):
    @http.route('/api/privy/doc_signing/', auth='public')
    def privy_doc_signing(self, **kw):
        request_data = request.jsonrequest
        response = request.env.user.partner_id.doc_signing(request_data)
        return response
        


