from odoo import models, fields, api, _

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    secondary_uom = fields.Many2one('uom.uom', 'Secondary UoM', related='product_id.secondary_uom_id')
    qty_of_secondary_uom = fields.Float('Quantity of Secondary UoM', compute='compute_qty_of_secondary_uom')
    date = fields.Datetime(string='Date', related='stock_move_id.date', store=True)

    def compute_qty_of_secondary_uom(self):
        self.qty_of_secondary_uom = 0
        if self.secondary_uom:
            if self.secondary_uom.factor_inv > 0:
                self.qty_of_secondary_uom = self.quantity/self.secondary_uom.factor_inv
