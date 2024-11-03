
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StockLotSerialize(models.TransientModel):
    _name = "stock.lot.serialize"
    _description = 'Stock Lot Serialize'

    picking_id = fields.Many2one('stock.picking', required=True)
    line_ids = fields.One2many('stock.lot.serialize.line', 'serializer_id')

    @api.model
    def default_get(self, field_list):
        res = super(StockLotSerialize, self).default_get(field_list)
        if 'line_ids' not in res:
            picking = self.env['stock.picking'].browse(res.get('picking_id', False))
            line_values = []
            for seq, move in enumerate(picking.move_lines.filtered(lambda o: o.product_id._is_lot_auto() and o.fulfillment < 100)):
                line_values += [(0, 0, {
                    'sequence': seq + 1,
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'demand_qty': move.product_uom_qty,
                    'qty_per_lot': move.product_uom_qty
                })]
            res['line_ids'] = line_values
        return res

    def action_confirm(self):
        self.ensure_one()
        self.picking_id.with_context(skip_serializer=True).action_serialize()


class StockLotSerializeLine(models.TransientModel):
    _name = "stock.lot.serialize.line"
    _description = 'Stock Lot Serialize Line'

    serializer_id = fields.Many2one('stock.lot.serialize')
    sequence = fields.Char(string='No.')
    move_id = fields.Many2one('stock.move')
    product_id = fields.Many2one('product.product')
    demand_qty = fields.Float(string="Demand")
    qty_per_lot = fields.Integer(string="Quantity Per Lot", related='move_id.qty_per_lot', readonly=False)


    @api.onchange('qty_per_lot', 'demand_qty')
    def _check_quantity(self):
        for record in self:
            if record.qty_per_lot > record.demand_qty:
                raise ValidationError(_("Quantity per lot must be less or equal to demand quantity."))
