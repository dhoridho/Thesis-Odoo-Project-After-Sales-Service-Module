from odoo import fields, models, api


class HrLeaveCancelationWizard(models.TransientModel):
    _name = 'hr.leave.cancelation.wizard'

    feedback = fields.Text()
    state = fields.Char()

    def submit(self):
        """ Prepare the Cash Advance feedback and trigger Approve. """
        self.ensure_one()
        hr_leave_cancel = self.env['hr.leave.cancelation'].browse(self._context.get('active_ids', []))
        hr_leave_cancel.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            hr_leave_cancel.action_approve()
        else:
             hr_leave_cancel.action_refuse()
