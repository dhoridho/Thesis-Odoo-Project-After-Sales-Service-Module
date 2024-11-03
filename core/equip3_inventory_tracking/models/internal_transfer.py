
from odoo import _, api, fields, models
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError, UserError


class InternalTransfer(models.Model):
    _inherit = 'internal.transfer'

    is_expired_tranfer = fields.Boolean(
        string="Expired Transfer", default=False)

    def action_confirm(self):
        for transfer in self:
            if not transfer.product_line_ids:
                raise ValidationError(_('Please add product lines'))
            if transfer.is_expired_tranfer:
                do_data = {
                    'location_id': transfer.source_location_id.id,
                    'location_dest_id': transfer.destination_location_id.id,
                    'move_type': 'direct',
                    'partner_id': transfer.create_uid.partner_id.id,
                    'scheduled_date': transfer.scheduled_date,
                    'picking_type_id': transfer.operation_type_out_id.id,
                    'origin': transfer.name,
                    'branch_id': transfer.branch_id and transfer.branch_id.id or False,
                    'transfer_id': transfer.id,
                }
                do_picking = self.env['stock.picking'].create(do_data)
                counter = 1
                for line in transfer.product_line_ids:
                    stock_move_obj = self.env['stock.move']
                    do_move_data = {
                        'move_line_sequence': counter,
                        'picking_id': do_picking.id,
                        'name': line.product_id.name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.qty,
                        'product_uom': line.uom.id,
                        'location_id': line.source_location_id.id,
                        'location_dest_id': line.destination_location_id.id,
                        'date': line.scheduled_date,
                    }
                    counter += 1
                    stock_move_obj.create(do_move_data)
                transfer.write({'state': 'confirm'})
            else:
                return super(InternalTransfer, self).action_confirm()
