from odoo import api, fields, models, _


class StockScrapRequest(models.Model):
    _inherit = 'stock.scrap.request'

    base_sync = fields.Boolean("Base Sync", default=False)

    @api.model
    def create(self, vals):
        if 'name' in vals:
            vals['name'] = '/'
        res = super().create(vals)
        return res

    def generate_sequence(self):
        stock_scrap_request = self.env["stock.scrap.request"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for x in stock_scrap_request:
            if x.base_sync:
                x.name = self.env["ir.sequence"].next_by_code("stock.product.usage")
                x.base_sync = False

        result = {
            "name": "Stock Scrap Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "stock.scrap.request",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", stock_scrap_request.ids)],
            "target": "current",
        }
        return result
