from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class CompleteProgressConfirmation(models.TransientModel):
    _name = 'complete.progress.confirmation'
    _description = 'Complete Progress Confirmation'

    txt_msg = fields.Text(string="Confirmation",default="Are you sure to complete progress?")
    progressive_claim_id = fields.Many2one('progressive.claim', string="Progressive Claim")
    reason = fields.Text('Reason')

    def action_confirm(self):
        self.progressive_claim_id.write({'complete_progress': True,
                                         'reason_complete_progress': self.reason})
