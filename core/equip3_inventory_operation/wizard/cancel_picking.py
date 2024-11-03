# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class CancelPicking(models.TransientModel):
    _name = "cancel.picking"
    _description = 'Cancel Picking'

    reason = fields.Text('Reason', required="1")

    def cancel_picking(self):
        active_ids = self._context.get('active_ids')
        picking_ids = self.env['stock.picking'].browse(active_ids)
        journal_cancel = picking_ids.journal_cancel
        user = self.env.user
        name = " Cancelled by %s at %s. Reason: " % (
            user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        for picking in picking_ids:
            if journal_cancel:
                picking.cancel_reason = name + self.reason
            if picking.transfer_id and picking.transfer_id.is_transit and picking.is_transfer_in and not picking.backorder_id:
                for line in picking.move_line_ids_without_package:
                    transist_line = picking.transfer_id.product_line_ids.filtered(
                        lambda r: r.product_id.id == line.product_id.id)
                    transist_line.write({'qty_cancel': line.qty_done})
            picking.action_cancel()
        return True
