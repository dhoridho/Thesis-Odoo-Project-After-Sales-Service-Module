from odoo import api, models, fields


class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.depends('quant_ids', 'quant_ids.quantity')
    def _product_qty(self):
        res = super(ProductionLot, self)._product_qty()
        for lot in self:
            stock_move_qty = self.env['stock.move'].search(
                [('next_lot_not_autogenerate', '=ilike', str(lot.name))], limit=1)
            if stock_move_qty:
                lot.product_qty = stock_move_qty.product_uom_qty
        return res
