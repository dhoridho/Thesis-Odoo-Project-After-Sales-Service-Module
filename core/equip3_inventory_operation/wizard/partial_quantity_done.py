# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class PartialQuantityDone(models.TransientModel):
    _name = "partial.quantity.done"
    _description = 'Partial Quantity Done'

    product_id = fields.Many2one('product.product', string="Product")
    done_qty = fields.Integer(string="Done")
    move_id = fields.Many2one('stock.move', string="Move")


    def action_confirm_partial_quantity(self):
        for record in self:
            if not (record.done_qty > 1 and record.done_qty < 100):
                raise ValidationError(_("Please Fill the percentage Of Done Quantity within 0-100"))
            if record.move_id.move_line_ids:
                for line in record.move_id.move_line_ids:
                    line.qty_done = (record.move_id.initial_demand * record.done_qty) / 100
                record.move_id.move_progress += record.done_qty
            else:
                record.move_id.quantity_done = (record.move_id.initial_demand * record.done_qty) / 100
        return True
