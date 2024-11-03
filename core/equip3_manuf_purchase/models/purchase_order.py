from odoo import models, fields, api, _


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    mrp_force_location_dest_id = fields.Many2one('stock.location', string='MRP Force Location')

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        vals = super(PurchaseOrderLine, self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        if self.mrp_force_location_dest_id:
            vals.update({'location_dest_id': self.mrp_force_location_dest_id.id})
        return vals

    def _create_stock_moves(self, picking):
        moves = super(PurchaseOrderLine, self)._create_stock_moves(picking)
        mrp_force_location_dest_ids = self.mapped('mrp_force_location_dest_id')
        mrp_location_dest_id = mrp_force_location_dest_ids and mrp_force_location_dest_ids[0] or False
        if mrp_location_dest_id is not False and picking.location_dest_id != mrp_location_dest_id:
            write_values = {'location_dest_id': mrp_location_dest_id.id}
            picking_type = self.env['stock.picking.type'].search([('default_location_dest_id', '=', mrp_location_dest_id.id)], limit=1)
            if picking_type:
                write_values.update({'picking_type_id': picking_type.id})
            picking.write(write_values)
        return moves
