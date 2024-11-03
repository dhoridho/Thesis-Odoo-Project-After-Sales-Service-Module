# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models


class Product(models.Model):
    _inherit = 'product.product'

    product_lots_ids = fields.One2many(
        'stock.production.lot', 'product_id', string="Product Lots", tracking=True)

    @api.model
    def search_product_expiry(self):
        res = super(Product, self).search_product_expiry()
        for key, val in res.get('day_wise_expire').items():
            total_qty = 0
            if val.get('product_id'):
                production_lot_ids = self.env['stock.production.lot'].browse(
                    val.get('product_id'))
                total_qty = sum(production_lot_ids.mapped('product_qty'))
            val['total_qty'] = total_qty
        return res
