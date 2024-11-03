# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo.exceptions import ValidationError, Warning
from odoo import api, tools, _, models, fields


class RentalPosOrder(models.Model):
    _name = 'rental.pos.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Rental Pos Order'
    _rec_name = 'full_product_name'

    order_line_id = fields.Many2one('pos.order.line')
    order_id = fields.Many2one(related="order_line_id.order_id", store=True)
    product_id = fields.Many2one(related="order_line_id.product_id", store=True)
    partner_id = fields.Many2one(related="order_id.partner_id", store=True)
    date_order = fields.Datetime(related="order_id.date_order", store=True)
    full_product_name = fields.Char(related="order_line_id.full_product_name", store=True)
    security_price = fields.Monetary(string="Security Price")
    price_unit = fields.Float(related="order_line_id.price_unit", store=True)
    qty = fields.Float(related="order_line_id.qty", store=True)
    price_subtotal = fields.Float(related="order_line_id.price_subtotal", store=True)
    price_subtotal_incl = fields.Float(related="order_line_id.price_subtotal_incl", store=True)
    currency_id = fields.Many2one(related="order_line_id.currency_id", store=True)
    is_rental_product = fields.Boolean(
        related="order_line_id.is_rental_product", store=True)
    selected_tenure_string = fields.Text(
        related="order_line_id.selected_tenure_string", store=True)
    state = fields.Selection(selection=[
        ('rented', 'Rented'),
        ('free', 'Free'),
        ('cancel', 'Cancelled'),
    ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='rented')
    refund_security_amount = fields.Monetary(
        'Refund Security Amount', currency_field='currency_id')
    extra_refund_amount = fields.Monetary(
        'Extra Refund Amount', currency_field='currency_id')
    deducted_amount = fields.Monetary(
        'Deducted Amount', currency_field='currency_id')
    return_date = fields.Datetime('Return/Refund Date')
    return_order = fields.Many2one('pos.order', 'Return Order')
