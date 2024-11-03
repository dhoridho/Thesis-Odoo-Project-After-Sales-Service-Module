# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

class StockWarehouse(models.Model):
    _name = 'stock.warehouse'
    _inherit = 'stock.warehouse'
    
    mp_account_ids = fields.One2many('mp.account', 'warehouse_id')


class StockMove(models.Model):
    _inherit = 'stock.move'
    _description = 'Stock Move'

    def write(self, vals):
        for rec in self:
            if not rec.date:
                vals['date'] = fields.Datetime.now()
        return super(StockMove, self).write(vals)


# class StockSaleAllocation(models.Model):
#     _name = 'stock.sale.allocation'
#     _description = 'Stock Sale Allocation'
#     
#     product_id = fields.Many2one('product.product')