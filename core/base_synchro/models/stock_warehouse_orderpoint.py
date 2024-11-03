from odoo import api, fields, models, _


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        stock_warehouse_orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for x in stock_warehouse_orderpoint:
            if x.base_sync:
                x.name = self.env["ir.sequence"].next_by_code("sequence.stock.warehouse.orderpoint")
                x.base_sync = False

        result = {
            "name": "Stock Warehouse Orderpoint Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "stock.warehouse.orderpoint",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", stock_warehouse_orderpoint.ids)],
            "target": "current",
        }
        return result
