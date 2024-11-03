from odoo import api, fields, models, _


class StockReturnMoveLine(models.TransientModel):
    _name = 'stock.return.move.line'
    _description = 'Stock Return Move Line'

    product_id = fields.Many2one('product.product', string='Product')
    return_id = fields.Many2one('stock.return.picking', string='Return')
    lot_id = fields.Many2one('stock.production.lot', string='Lot')
    qty = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', string='Uom')
