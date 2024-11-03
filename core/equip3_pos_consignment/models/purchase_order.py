# -*- coding: utf-8 -*-

from odoo import fields, models

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sold_qty = fields.Float(string='Sold', default=0.0)
    sold_price = fields.Float(string='Sold Price', default=0.0)