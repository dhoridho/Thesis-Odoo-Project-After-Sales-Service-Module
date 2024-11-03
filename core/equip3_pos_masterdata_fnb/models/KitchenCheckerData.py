# -*- encoding: utf-8 -*-

from odoo import models, fields, api

class KitchenCheckerData(models.Model):
    _name = "kitchen.checker.data"
    _description = "Kitchen Checker Data"

    pos_order_name = fields.Char(string='Receipt Number')
    product_id = fields.Many2one('product.product', string='Product')
    product_qty = fields.Float(string='Product Quantity')
    table_id = fields.Many2one('restaurant.table', string='Table', help='The table where this order was served', index=True)
    floor_id = fields.Many2one('restaurant.floor', string='Floor')

    @api.model
    def set_checker_data(self, vals):
        rec = self.create({
            'pos_order_name':vals.get('pos_order_name'),
            'product_id':vals.get('product_id'),
            'product_qty':vals.get('product_qty'),
            'table_id':vals.get('table_id'),
            'floor_id':vals.get('floor_id'),
        })
        return {'success': True}

    @api.model
    def remove_checker_data(self, vals):
        existing_data = self.search([('pos_order_name', '=', vals.get('pos_order_name'))])
        if existing_data:
            existing_data.unlink()

    @api.model
    def get_checker_data(self):
        res = self.search_read([], ['pos_order_name', 'product_id', 'product_qty', 'table_id', 'floor_id', 'create_date'])
        return res