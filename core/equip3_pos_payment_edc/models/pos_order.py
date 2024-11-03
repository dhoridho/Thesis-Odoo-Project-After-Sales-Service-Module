# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError


class PosOrder(models.Model):
    _inherit = "pos.order"
 
    is_payment_edc = fields.Boolean('Is Payment EDC?')
    payment_edc_id = fields.Many2one('pos.payment.edc', string="Payment EDC")

    @api.model
    def _process_order(self, order, draft, existing_order):
        res = super(PosOrder,self)._process_order(order, draft, existing_order) 
        if res:
            order = self.env['pos.order'].sudo().search([('id','=', res)])
            if order and order.payment_edc_id and order.state in ['paid']:
                values = {
                    'pos_order_id': order.id,
                }
                order.payment_edc_id.write(values)

        return res

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder,self)._order_fields(ui_order)
        res.update({
            'is_payment_edc': ui_order.get('is_payment_edc') or False,
            'payment_edc_id': ui_order.get('payment_edc_id') or False,
        })
        return res

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        res = super(PosOrder,self)._payment_fields(order, ui_paymentline)
        res.update({
            'is_payment_edc': ui_paymentline.get('is_payment_edc') or False,
            'approval_code': ui_paymentline.get('approval_code') or False,
            'installment_tenor': ui_paymentline.get('installment_tenor') or False,
            'installment_amount': ui_paymentline.get('installment_amount') or False,
        })
        return res

    def _prepare_void_order_vals(self, order, vals):
        values = super(PosOrder,self)._prepare_void_order_vals(order=order, vals=vals)

        values['is_payment_edc'] = order.is_payment_edc
        values['payment_edc_id'] = order.payment_edc_id and order.payment_edc_id.id or False

        return values


    def _prepare_void_order_payment_vals(self, order, payment):
        values = super(PosOrder,self)._prepare_void_order_payment_vals(order=order, payment=payment)

        values['is_payment_edc'] = payment.is_payment_edc
        values['approval_code'] = payment.approval_code
        values['installment_tenor'] = payment.installment_tenor
        values['installment_amount'] = payment.installment_amount

        return values