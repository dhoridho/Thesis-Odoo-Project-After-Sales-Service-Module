from odoo import models, fields, api


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    cutting_unit = fields.Boolean(related="product_id.is_cutting_product")
    cutting_uom = fields.Many2one(related='product_id.cutting_unit_measure')
    cutting_line_id = fields.Many2one('cutting.order.line', string='Cutting Order Line')
    original_lot_id = fields.Many2one('stock.production.lot', string='Original Lot/Serial Number')
    is_cutted = fields.Boolean(string='Is Cutted')
    last_cutting_value = fields.Float(string='Last Cutting Value', digits='Product Unit of Measure') 

    length = fields.Float(string='Length', digits='Product Unit of Measure', default=1.0)
    width = fields.Float(string='Width', digits='Product Unit of Measure', default=1.0)
    height = fields.Float(string='Height', digits='Product Unit of Measure', default=1.0)
    volume = fields.Float(string='Volume', compute='_compute_volume', digits='Product Unit of Measure', store=True)

    @api.depends('product_qty', 'length', 'width', 'height')
    def _compute_volume(self):
        for line in self:
            volume = 1.0
            for variable in [line.length, line.width, line.height]:
                volume *= variable > 0.0 and variable or 1.0
            line.volume = volume
