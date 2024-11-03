# -*- coding: utf-8 -*-

from odoo import api, models, fields


class POSProductAttribute(models.Model):
    _name = "pos.product.attribute"
    _description = "Allow cashier add multi attribute to Main Product"

    sequence = fields.Integer('Sequence No.', default=0)
    product_id = fields.Many2one('product.product', string='Main Product', required=1)

    @api.onchange('attribute_id')
    def onchange_attribute_id(self):
        if self.attribute_id:
            self.value_ids = [[6, 0, [v.id for v in self.attribute_id.value_ids]]]