
from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class ApprovalMatrixReject(models.TransientModel):
    _name = 'approval.matrix.action.checklist.reject'

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        checklist_id = self.env['action.checklist'].browse([self._context.get('active_id')])
        if checklist_id.is_hse_action_approval_matrix == True:
            approving_matrix_line = sorted(checklist_id.action_checklist_user_ids.filtered(lambda r: r.is_approve == False))
            if approving_matrix_line:
                matrix_line = approving_matrix_line[0]
                matrix_line.write({'feedback': self.reason})
                checklist_id.action_reject_approval()
        else:
            checklist_id.write({'state': 'reject',
                                'reason': self.reason})
