from odoo import models, fields, api, _


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    daily_activity_id = fields.Many2one('agriculture.daily.activity', string='Plantation Plan')
    activity_line_id = fields.Many2one('agriculture.daily.activity.line', string='Plantation Lines')
    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Plantation Record')

    stock_move_line_id = fields.Many2one('stock.move.line', string='Move Line')

    @api.depends('stock_move_id', 'stock_move_id.lot_ids', 'stock_move_line_id', 'stock_move_line_id.lot_id')
    def _compute_move_lots(self):
        super(StockValuationLayer, self)._compute_move_lots()
        for record in self.filtered(lambda o: o.stock_move_line_id):
            record.move_lot_ids = [(6, 0, [record.stock_move_line_id.lot_id.id])]
