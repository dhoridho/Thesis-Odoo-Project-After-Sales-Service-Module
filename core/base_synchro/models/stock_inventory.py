from odoo import api, fields, models, _


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        stock_inventory = self.env["stock.inventory"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for x in stock_inventory:
            if x.base_sync:
                x.name = self.env["ir.sequence"].next_by_code("inv.adj.seq")
                x.base_sync = False

        result = {
            "name": "Stock Count Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "stock.inventory",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", stock_inventory.ids)],
            "target": "current",
        }
        return result
