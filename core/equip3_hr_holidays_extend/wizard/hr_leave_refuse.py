from odoo import fields, models, api


class HrLeaveRefuseWizard(models.TransientModel):
    _name = 'hr.leave.wizard'

    feedback = fields.Text()
    state = fields.Char()

    def submit(self):
        """ Prepare the Cash Advance feedback and trigger Approve. """
        self.ensure_one()
        hr_leave = self.env['hr.leave'].browse(self._context.get('active_ids', []))
        hr_leave.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            hr_leave.action_approve()
        else:
             hr_leave.action_refuse()
