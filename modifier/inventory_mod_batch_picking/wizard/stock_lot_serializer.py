
from odoo import api, fields, models, _


class StockLotSerializeInherit(models.TransientModel):
    _inherit = "stock.lot.serialize"
    _description = 'Stock Lot Serialize'

    picking_batch_id = fields.Many2one('stock.picking.batch', string='Picking')
    is_picking_batch = fields.Boolean(string='Is Picking Batch', store=True)
    stock_batch_move_line_ids = fields.One2many('stock.lot.serialize.line', 'stock_move_batch_id', string="Stock Quant", compute='_compute_stock_batch_ids',  inverse='_inverse_stock_batch_move_line_ids',store=True)

    def _inverse_stock_batch_move_line_ids(self):
        pass

    @api.depends('picking_batch_id')
    def _compute_stock_batch_ids(self):
        if not self.env.context.get('default_is_picking_batch', False):
            return
        else:
            for record in self:
                record.stock_batch_move_line_ids = []
                stock_pick = self.picking_batch_id
                data = []
                counter = 1
                filter_move_lot_line = stock_pick.move_ids.filtered(lambda r:r.product_id.tracking == 'lot' and r.product_id.is_in_autogenerate and r.fulfillment < 100)
                for move in filter_move_lot_line:
                    product_line = {
                        'sequence': counter,
                        'product_id': move.product_id.id,
                        'demand_qty': move.product_uom_qty,
                    }
                    counter += 1
                    data.append((0, 0, product_line))
                record.stock_batch_move_line_ids = data

    def confirm_batch_by_lots(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids')
        stock_pick = self.picking_batch_id
        stock_pick_serial_line = stock_pick.move_ids.filtered(lambda r:r.product_id.tracking == 'serial' and r.product_id.is_sn_autogenerate and r.fulfillment < 100)
        if stock_pick_serial_line:
            for move in stock_pick_serial_line:
                move._generate_serial_numbers()
            stock_pick._reset_sequence()
        for line in self.stock_batch_move_line_ids:
            filter_move_lot_line = stock_pick.move_ids.filtered(lambda r:r.product_id.tracking == 'lot' and r.product_id.id == line.product_id.id and r.product_id.is_in_autogenerate and r.fulfillment < 100)
            filter_move_lot_line.move_line_nosuggest_ids.unlink()
            filter_move_lot_line.write({'qty_per_lot': line.qty_per_lot})
            filter_move_lot_line.action_assign_lot_number()


class StockLotSerializeLineInherit(models.TransientModel):
    _inherit = "stock.lot.serialize.line"
    _description = 'Stock Lot Serialize Line'

    stock_move_batch_id = fields.Many2one('stock.lot.serialize', string="Stock Quant")
