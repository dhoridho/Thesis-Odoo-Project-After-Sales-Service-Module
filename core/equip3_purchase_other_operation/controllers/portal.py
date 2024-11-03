# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from ...sh_rfq_portal.controllers.portal import PurchaseRFQPortal

class PurchaseRFQPortal(PurchaseRFQPortal):

    @http.route(['/my/rfq/<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_rfq_form(self, quote_id, report_type=None, access_token=None, message=False, download=False, **kw):
        quote_sudo = request.env['purchase.order'].sudo().browse(quote_id)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=quote_sudo, report_type=report_type, report_ref='purchase.report_purchase_quotation', download=download)
        values = {
            'token': access_token,
            'quotes': quote_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.partner_id.id,
            'report_type': 'html',
        }
        if quote_sudo.not_editable and quote_sudo.is_editable:
            return request.render('equip3_purchase_other_operation.purchase_tender_portal_my_rfq_order_update', values)
        else:
            return request.render('sh_rfq_portal.portal_rfq_form_template', values)
