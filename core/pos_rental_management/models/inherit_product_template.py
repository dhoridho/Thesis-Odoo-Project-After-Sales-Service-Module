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
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from datetime import date, timedelta, datetime


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_for_rent = fields.Boolean(string="Available For Rent")
    is_security_required = fields.Boolean(string="Is Security Amount Required")
    rental_security_amount = fields.Monetary(
        string='Security Amount', currency_field='currency_id')
    rental_tenure_ids = fields.One2many(
        'rental.product.tenure', 'product_tmpl_id', string="Rental Product Tenure")

    
    @api.constrains('rental_tenure_ids','available_for_rent')
    def check_tenure_ids(self):
        if self.available_for_rent and not self.rental_tenure_ids:
            raise ValidationError('Cannot make this product available for rent without adding rental product tenure details.')


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_rental_product = fields.Boolean('Rental Product')
    rental_note = fields.Text(string='Rental Description')
    selected_tenure_string = fields.Text(string='Selected Tenure String')
    related_product_name = fields.Char(string='Related Product name')
    added_tenure_count = fields.Integer(string='Added Tenure Count')
    rental_price = fields.Monetary(
        string='Rental Price Unit', currency_field='currency_id')
    security_price = fields.Monetary(
        string='Security Price', currency_field='currency_id')
    rental_security_line_id = fields.Integer('Security Product Line ID')
    rental_id = fields.Many2one('rental.pos.order')
    refund_security_amount = fields.Monetary('Refund Security Amount', currency_field='currency_id')
    extra_refund_amount = fields.Monetary('Extra Refund Amount', currency_field='currency_id')
    deducted_amount = fields.Monetary('Deducted Amount', currency_field='currency_id')

    @api.model
    def _order_line_fields(self, line, session_id=None):
        line_data = super(PosOrderLine, self)._order_line_fields(
            line, session_id=None)
        line_data[2].update(
            {
                'is_rental_product': line[2].get('is_rental_product', False),
                'selected_tenure_string': line[2].get('selected_tenure_string', False),
                'rental_price': line[2].get('rental_price', False),
                'added_tenure_count': line[2].get('added_tenure_count', False),
                'rental_note': line[2].get('rental_note', False),
                'security_price': line[2].get('security_price', False),
                'related_product_name': line[2].get('related_product_name', False),
                'refund_security_amount': line[2].get('refund_security_amount', False),
                'extra_refund_amount': line[2].get('extra_refund_amount', False),
                'deducted_amount': line[2].get('deducted_amount', False),
            })
        return line_data

    @api.constrains('is_rental_product')
    def is_order_rental(self):
        if self.is_rental_product and self.order_id and not self.order_id.is_rental_order:
            self.order_id.is_rental_order = True


class UomUom(models.Model):
    _inherit = 'uom.uom'

    is_rental_uom = fields.Boolean('Rental UOM')
