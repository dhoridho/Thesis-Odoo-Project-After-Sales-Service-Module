from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta


class StockMoveWarranty(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        res = super(StockMoveWarranty, self)._action_done(cancel_backorder=cancel_backorder)
        self.create_warranty()
        return res

    def create_warranty(self):
        stock_force_date_app = self.env['ir.module.module'].sudo().search([('name', '=', 'stock_force_date_app'), ('state', '=', 'installed')])
        for move_line in self.move_line_ids.filtered(lambda x: x.product_id.tracking == 'serial' and x.lot_id and x.product_id.under_warranty and x.picking_id.picking_type_code == 'outgoing'):
            vals = {
                'picking_id': move_line.picking_id.id,
                'partner_id': move_line.picking_id.partner_id.id,
                'product_id': move_line.product_id.id,
                'product_serial_id': move_line.lot_id.id,
                'warranty_type': move_line.product_id.warranty_type,
                'warranty_create_date': move_line.picking_id.force_date if stock_force_date_app and move_line.picking_id.force_date else fields.Datetime.now(),
                'warranty_end_date': move_line.picking_id.force_date + relativedelta(months=move_line.product_id.warranty_period) if stock_force_date_app and move_line.picking_id.force_date else fields.Datetime.now() + relativedelta(months=move_line.product_id.warranty_period),
            }
            print("➡ vals :", vals)
            product_warranty = self.env['product.warranty'].create(vals)
            if product_warranty:
                product_warranty.state_update()
        return True
