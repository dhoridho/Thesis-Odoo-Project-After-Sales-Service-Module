from odoo import models, fields, api, _
from datetime import datetime, timedelta


class PurchaseRequestRejectWizard(models.TransientModel):
    _name = 'purchase.request.reject.wizard'

    reject_reason = fields.Text('Reject Reason')

    def action_reject(self):
        line_obj = self.env['rfq.variable.line'].browse(self.env.context.get('active_id'))
        if line_obj:
            line_obj.write({'feedback': self.reject_reason, 'state': 'cancelled'})
        return True
