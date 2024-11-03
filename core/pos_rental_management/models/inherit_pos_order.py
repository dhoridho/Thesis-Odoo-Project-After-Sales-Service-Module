# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import api, fields, models


class InheritPosOrder(models.Model):
    _inherit = "pos.order"

    invoice_remark = fields.Char(string="Invoice Remark")
    is_partially_paid = fields.Boolean(string="Is Partially Paid", copy=False)
    is_rental_order = fields.Boolean(string="Is Rental Order", copy=False)
    is_return_order = fields.Boolean(string='Return Order', copy=False)
    wk_order_amount = fields.Float(string="Total")
    rental_number = fields.Integer('Rental Number')
    rented_count = fields.Integer('Rented Product Counts')
    rental_order_ids = fields.One2many('rental.pos.order', 'order_id')
    refund_security_amount = fields.Monetary('Refund Security Amount')
    extra_refund_amount = fields.Monetary('Extra Refund Amount')
    deducted_amount = fields.Monetary('Deducted Amount')

    @api.model
    def _order_fields(self, ui_order):
        data = super(InheritPosOrder, self)._order_fields(ui_order)
        data.update({
            'invoice_remark': ui_order.get('invoice_remark', False),
            'is_partially_paid': ui_order.get('is_partially_paid', False),
            'is_return_order': ui_order.get('is_return_order', False),
            'rental_number': ui_order.get('rental_number', False),
            'refund_security_amount': ui_order.get('refund_security_amount', False),
            'extra_refund_amount': ui_order.get('extra_refund_amount', False),
            'deducted_amount': ui_order.get('deducted_amount', False),
        })
        return data

    @api.model
    def create_from_ui(self, orders, draft=False):
        data = return_data = super(
            InheritPosOrder, self).create_from_ui(orders, draft)
        if type(data) == dict:
            order_ids = [res.get('id') for res in return_data.get('order_ids')]
        else:
            order_ids = [res.get('id') for res in data]
        order_objs = self.browse(order_ids)
        for order in order_objs:
            if order.account_move:
                order.account_move.partial_payment_remark = order.invoice_remark
                if order.is_partially_paid:
                    order.wk_order_amount = order.amount_total
                    order.amount_total = order.amount_paid
            if order.is_return_order and order.rental_number:
                rental_data = self.env['rental.pos.order'].browse(
                    order.rental_number)
                if rental_data.exists():
                    rental_data.write({
                        'refund_security_amount': order.refund_security_amount,
                        'extra_refund_amount': order.extra_refund_amount,
                        'deducted_amount': order.deducted_amount,
                        'state': 'free',
                        'return_date': order.date_order,
                        'return_order': order.id
                    })
            for line in order.lines:
                if line.is_rental_product:
                    values = {
                        'order_line_id': line.id,
                        'security_price': line.product_id.rental_security_amount if line.product_id.is_security_required else 0
                    }
                    rental_id = self.create_rental_order(values)
                    line.rental_id = rental_id
                    order.write({
                        'rental_order_ids': [(4, 0, rental_id)]
                    })
                    order.rented_count += 1
        return return_data

    def action_pos_order_paid(self):
        if self.is_partially_paid:
            self.write({'state': 'paid'})
        return super(InheritPosOrder, self).action_pos_order_paid()

    def create_rental_order(self, values):
        if values:
            rental_id = self.env['rental.pos.order'].create(values)
            return rental_id

    def action_rental_orders(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'pos_rental_management.pos_rental_order_action')
        action['context'] = {}
        action['domain'] = [('id', 'in', self.rental_order_ids.ids)]
        return action

    @api.model
    def _process_order(self, order, draft, existing_order):
        # -------- for rented return product -----------------
        data = order.get('data')
        if data.get('is_return_order'):
            data['amount_paid'] = 0
            for statement in data.get('statement_ids'):
                statement_dict = statement[2]
                if data['amount_total'] < 0:
                    statement_dict['amount'] = statement_dict['amount'] * -1
                else:
                    statement_dict['amount'] = statement_dict['amount']
            if data['amount_total'] < 0:
                data['amount_tax'] = data.get('amount_tax')
                data['amount_return'] = 0
                data['amount_total'] = data.get('amount_total')
        res = super(InheritPosOrder, self)._process_order(
            order, draft, existing_order)
        return res
