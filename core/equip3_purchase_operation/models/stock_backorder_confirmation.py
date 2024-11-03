from odoo import models


class StockBackorderConfirm(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def process(self):
        res = super().process()
        for pick_id in self.pick_ids:
            if pick_id.purchase_id:
                pick_id.purchase_id.is_backorder = True
        return res