from odoo import models, api


class StockWarehousePragmatic(models.Model):
    _inherit = 'stock.warehouse'

    @api.model
    def create(self, vals):
        res = super(StockWarehousePragmatic, self).create(vals)
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])
        order_stages = self.env['order.stage'].search([])
        for rec in order_stages:
            if warehouse_ids not in rec.warehouse_ids:
                rec.warehouse_ids = [(6, 0, warehouse_ids.ids)]
        return res