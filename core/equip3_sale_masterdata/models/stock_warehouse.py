from odoo import models, fields, api, _


class StockWarehouseInherit(models.Model):
    _inherit = 'stock.warehouse'

    default_delivery_location_id = fields.Many2one(comodel_name='stock.location', string='Default Delivery Location', domain="[('warehouse_id','=',id),('usage','=','internal')]")

    @api.model
    def create(self, vals):
        res = super(StockWarehouseInherit, self).create(vals)
        if not res.default_delivery_location_id:
            res.default_delivery_location_id = res.lot_stock_id
        return res
    