
from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class ApprovalMatrixsaleReject(models.TransientModel):
    _name = 'approval.matrix.job.reject.const'
    _description = "Approval Matrix Job Estimate Reject"

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        job_id = self.env['job.estimate'].browse([self._context.get('active_id')])
        approving_matrix_line = sorted(job_id.job_estimate_user_ids.filtered(lambda r: r.is_approve == False))
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            matrix_line.write({'feedback': self.reason})
            job_id.action_reject_approval()
            
