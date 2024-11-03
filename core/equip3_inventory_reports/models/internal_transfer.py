from odoo import fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError


class InternalTransfer(models.Model):
    _inherit = "internal.transfer"

    arrival_date = fields.Datetime(
        string="Arrival Date", default=datetime.now())

    def action_confirm(self):
        """ Refactored. So that the function in equip3_inventory_operation is not overridden. """
        for transfer in self:
            mr_id = transfer.mr_id
            if mr_id:
                mr_id._check_processed_record(mr_id.id, transfer.id) # `mr_id.id` parameter should be omitted.
        return super(InternalTransfer, self).action_confirm()

    def _prepare_transfer_vals(self, location_id, location_dest_id, scheduled_date, picking_type_id, branch_id):
        """ Not sure why `scheduled_date` is being replaced by `arrival_date`, 
        while `scheduled_date` is the key value of the inventory line groups. 
        But that's how it was in the previous code, so I'll leave it like that. """
        schedule_date = self.arrival_date
        return super(InternalTransfer, self)._prepare_transfer_vals(location_id, location_dest_id, scheduled_date, picking_type_id, branch_id)


class InternalTransferLine(models.Model):
    _inherit = "internal.transfer.line"

    def _prepare_transfer_line_vals(self, location_id, location_dest_id, picking, date, sequence):
        """ Same reason with `scheduled_date` on internal transfer. """
        date = self.product_line.arrival_date
        return super(InternalTransferLine, self)._prepare_transfer_line_vals(location_id, location_dest_id, picking, date, sequence)
