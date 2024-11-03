from odoo import models, fields, api, _


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    def post_inventory(self):
        self = self.with_context(bypass_cost_per_warehouse=True)
        return super(StockInventory, self).post_inventory()
