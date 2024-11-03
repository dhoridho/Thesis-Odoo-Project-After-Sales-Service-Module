# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

class ShProductTemplate(models.Model):
    _inherit = 'product.template'

    barcode_line_ids = fields.One2many(
        related='product_variant_ids.barcode_line_ids', readonly=False,ondelete='cascade')    

class ShProduct(models.Model):
    _inherit = 'product.product'

    barcode_line_ids = fields.One2many(
        'product.template.barcode', 'product_id', 'Barcode Lines')

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            args = expression.OR([args, [('barcode_line_ids.name', operator, name)]])
        return super(ShProduct, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)    

class ShProductBarcode(models.Model):
    _name = 'product.template.barcode'
    _description = "Product Barcode"

    product_id = fields.Many2one('product.product', 'Product', required=True, ondelete='cascade')
    name = fields.Char("Barcode", required=True)

    _sql_constraints = [
        ('unique_product_name', 'UNIQUE(product_id,name)', 'Barcode must be unique!')
    ]
