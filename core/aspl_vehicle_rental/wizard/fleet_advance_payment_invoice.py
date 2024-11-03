# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class FleetAdvancePaymentInvoice(models.TransientModel):
    _name = "fleet.advance.payment.invoice"
    _description = "Fleet Advance Payment Invoice"

    @api.model
    def _count(self):
        return len(self._context.get('active_ids', []))

    @api.model
    def _get_advance_payment_method(self):
        if self._count() == 1:
            rental_obj = self.env['fleet.vehicle.order']
            order = rental_obj.browse(self._context.get('active_ids'))[0]
            if order.invoice_count:
                return 'all'
        return 'delivered'

    @api.model
    def _default_product_id(self):
        product_id = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
        return self.env['product.product'].browse(int(product_id))

    @api.model
    def _default_deposit_account_id(self):
        return self._default_product_id().property_account_income_id

    @api.model
    def _default_deposit_taxes_id(self):
        return self._default_product_id().taxes_id

    advance_payment_method = fields.Selection([
        ('delivered', 'Invoiceable lines'),
        ('all', 'Invoiceable lines (deduct down payments)'),
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')
    ], string='What do you want to invoice?', default=_get_advance_payment_method, required=True)
    product_id = fields.Many2one('product.product', string='Down Payment Product', domain=[('type', '=', 'service')],
                                 default=_default_product_id)
    count = fields.Integer(default=_count, string='# of Orders')
    amount = fields.Float('Down Payment Amount', digits=dp.get_precision('Account'),
                          help="The amount to be invoiced in advance, taxes excluded.")
    deposit_account_id = fields.Many2one("account.account", string="Income Account",
                                         domain=[('deprecated', '=', False)],
                                         help="Account used for deposits", default=_default_deposit_account_id)
    deposit_taxes_id = fields.Many2many("account.tax", string="Customer Taxes", help="Taxes used for deposits",
                                        default=_default_deposit_taxes_id)

    def _create_invoice(self, order, ro_line, amount):
        inv_obj = self.env['account.move']
        vehicle_lines = self.env['fleet.vehicle.order']
        invoice_line = []

        account_id = False
        if self.product_id.id:
            account_id = self.product_id.property_account_income_id.id

        if self.amount <= 0.00:
            raise UserError(_('The value of the down payment amount must be positive.'))

        if self.advance_payment_method == 'percentage':
            amount = order.untaxed_amount * self.amount / 100
            name = _("Down payment of %s%%") % (self.amount,)
        else:
            amount = self.amount
            name = _('Down Payment')

        taxes = self.product_id.taxes_id
        tax_ids = taxes.ids

        invoice = inv_obj.create({
            'name': order.res_number,
            'origin': order.res_number,
            'partner_id': order.customer_name.id,
            'type': 'out_invoice',
            'reference': False,
            'account_id': order.customer_name.property_account_receivable_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': name,
                'account_id': account_id,
                'price_unit': amount,
                'product_id': self.product_id.id,
                'invoice_line_tax_ids': [(6, 0, tax_ids)],
            })],
            'currency_id': order.pricelist_id.currency_id.id,
            'user_id': order.user_id.id,
        })
        invoice.compute_taxes()
        invoice.message_post_with_view('mail.message_origin_link',
                                       values={'self': invoice, 'origin': order},
                                       subtype_id=self.env.ref('mail.mt_note').id)
        return invoice

    def create_invoices(self):
        rental_orders = self.env['fleet.vehicle.order'].browse(self._context.get('active_ids', []))

        if self.advance_payment_method == 'delivered':
            rental_orders.action_invoice_create()
        elif self.advance_payment_method == 'all':
            rental_orders.action_invoice_create(final=True)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id', self.product_id.id)

            rental_line_obj = self.env['vehicle.order.line']
            for order in rental_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.untaxed_amount * self.amount / 100
                else:
                    amount = self.amount
                taxes = self.product_id.taxes_id
                tax_ids = taxes.ids
                ro_line = rental_line_obj.create({
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'price': amount,
                    'vehicle_order_id': order.id,
                    'tax_id': [(6, 0, tax_ids)],
                })
                self._create_invoice(order, ro_line, amount)
        if self._context.get('open_invoices', False):
            return rental_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}

    def _prepare_deposit_product(self):
        return {
            'name': 'Down payment',
            'type': 'service',
            'invoice_policy': 'order',
            'property_account_income_id': self.deposit_account_id.id,
            'taxes_id': [(6, 0, self.deposit_taxes_id.ids)],
        }
