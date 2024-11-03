from odoo import api, fields, models, _


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        res = super(StockImmediateTransfer, self).process()
        context = dict(self.env.context) or {}
        if context.get("active_model") not in ['sale.order', 'purchase.order']:
            picking_ids = self.env['stock.picking'].browse(self.env.context.get('button_validate_picking_ids'))
            for picking_id in picking_ids:
                if picking_id.transfer_id and picking_id.state == 'done':
                    picking_id.transfer_id.calculate_transfer_qty(picking_id)
                if picking_id.transfer_id and 'Return' in picking_id.origin:
                    for line in picking_id.move_line_ids_without_package:
                        transist_line = picking_id.transfer_id.product_line_ids.filtered(lambda r: r.product_id.id == line.product_id.id)
                        transist_line.write({'return_qty': line.qty_done})
        return res
