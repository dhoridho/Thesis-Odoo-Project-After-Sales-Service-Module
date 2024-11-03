# coding: utf-8

from odoo import models, api, fields


class AcsCancelReason(models.TransientModel):
    _name = 'acs.cancel.reason'
    _description = "Reject Reason"

    cancel_reason = fields.Text(string="Reason", required=True)

    def cancel_appointment(self):
        record = self.env['hms.appointment'].search([('id','=',self.env.context.get('active_id'))])
        record.cancel_reason = self.cancel_reason
        record.appointment_cancel()
        return True

