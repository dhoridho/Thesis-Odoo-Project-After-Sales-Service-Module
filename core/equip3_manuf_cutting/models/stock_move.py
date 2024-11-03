from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = 'stock.move'

    sml_cutting_unit = fields.Boolean(related="product_id.is_cutting_product")
    cutting_line_id = fields.Many2one('cutting.order.line', string='Cutting Order Line')

    def _account_entry_move(self, qty, description, svl_id, cost):
        if self.cutting_line_id:
            # cutting.order model instead
            return False
        return super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    cutting_uom = fields.Many2one(related='product_id.cutting_unit_measure', string="Cutting UOM")

    length = fields.Float('Length', default=1.0)
    width = fields.Float('Width', default=1.0)
    height = fields.Float('Height', default=1.0)

    @api.onchange('length')
    def onchange_length(self):
        if self.length <= 0:
            raise ValidationError(_('Length value must be greater than 0!'))

    @api.onchange('width')
    def onchange_width(self):
        if self.width <= 0:
            raise ValidationError(_('Width value must be greater than 0!'))

    @api.onchange('height')
    def onchange_height(self):
        if self.height <= 0:
            raise ValidationError(_('Height value must be greater than 0!'))
