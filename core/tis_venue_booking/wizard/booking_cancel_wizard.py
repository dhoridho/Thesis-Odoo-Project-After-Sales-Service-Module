# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models,_
from odoo.exceptions import UserError


class CancelBooking(models.TransientModel):
    _name = 'cancel.booking'
    _description = "wizard for booking cancellation"

    lost_reason_id = fields.Many2one('lost.reason', string="Booking Lost Reason")
    text = fields.Text(string="Description")

    def action_lost_reason_apply(self):
        bookings = self.env['booking.booking'].browse(self.env.context.get('active_ids'))
        if bookings.invoice_ids:
            for rec in bookings.invoice_ids:
                if rec.state == 'draft':
                    for values in bookings:
                        values['lost_reason'] = self.lost_reason_id.name
                        values['description'] = self.text
                        values['state'] = 'cancel'
                    rec.button_cancel()
                else:
                    raise UserError(_('The related Invoice is already posted, '
                                      'so you cannot cancel the booking.'))
        else:
            for values in bookings:
                values['lost_reason'] = self.lost_reason_id.name
                values['description'] = self.text
                values['state'] = 'cancel'





