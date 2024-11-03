from odoo.addons.website_sale.controllers.main import WebsiteSale

from odoo import http,_
from odoo.http import request
from datetime import datetime

class WebsiteSaleStock(WebsiteSale):
    @http.route()
    def payment_transaction(self, *args, **kwargs):
        res = super(WebsiteSaleStock, self).payment_transaction(*args, **kwargs)
        Param = request.env['res.config.settings'].sudo().get_values()
        move_obj = request.env['account.move'].sudo()
        move_line = request.env['account.move.line'].sudo()
        if Param.get('automatic_confirm_saleorder'):
            order = request.website.sale_get_order()
            order.action_confirm()
            if Param.get('automatic_invoice_create'):
                order._create_invoices()
                invoice_id = order.invoice_ids
                invoice_id.action_post()
                picking_order = request.env['picking.order'].sudo().search([('sale_order','=',order.id)])
                picking_order.invoice = invoice_id.id
        return res
