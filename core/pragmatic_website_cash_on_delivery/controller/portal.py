from odoo import api, fields, models,_
import odoo
from odoo import http, _
from odoo.http import request
import json
from odoo.exceptions import UserError
from odoo import models,_
from odoo.exceptions import AccessDenied

class shop(http.Controller):

    @http.route(['/shop/confirmation/cash'], type='http', auth="public", website=True, sitemap=False)
    def payment_confirmation_cash_on_delivery(self, **post):
        sale_order_id = request.session.get('sale_last_order_id')
        order = request.env['sale.order'].sudo().browse(sale_order_id)
        msg = request.env['cash.delivery'].sudo().search([])
        payment_term_id = request.env['account.payment.term'].sudo().search([('name','=','Cash On Delievery')],limit=1)
        order.write({"state":"draft"})
        if payment_term_id:
            order.write({"payment_term_id":payment_term_id.id})
        Param = request.env['res.config.settings'].sudo().get_values()
        if Param.get('automatic_confirm_saleorder'):
            order.action_confirm()
            if Param.get('automatic_invoice_create'):
                order._create_invoices()
                order.invoice_ids.action_post()
                picking_order = request.env['picking.order'].sudo().search([('sale_order', '=', order.id)])
                picking_order.invoice = order.invoice_ids.id
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            return request.render("pragmatic_website_cash_on_delivery.confirmation_cash", {'order': order,'msg':msg})
        
       
