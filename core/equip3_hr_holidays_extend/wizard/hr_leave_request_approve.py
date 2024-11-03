from odoo import fields, models, api


class HrLeaveRequestApproveWizard(models.TransientModel):
    _name = 'hr.leave.request.wizard'

    feedback = fields.Text()
    state = fields.Char()
    
    def submit(self):
        """ Prepare the Cash Advance feedback and trigger Approve. """
        self.ensure_one()
        hr_leave_request_approve = self.env['hr.leave'].browse(self._context.get('active_ids', []))
        hr_leave_request_approve.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            hr_leave_request_approve.action_approve()
        else:
             hr_leave_request_approve.action_refuse()
