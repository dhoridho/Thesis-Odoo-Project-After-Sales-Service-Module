from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    original_lot_id = fields.Many2one('stock.production.lot', string='Original Lot/Serial Number', related='lot_id.original_lot_id')
