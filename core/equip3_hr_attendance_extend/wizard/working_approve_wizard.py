from odoo import fields, models, api


class HrWorkingSheetWizard(models.TransientModel):
    _name = 'hr.working.sheet.wizard'

    feedback = fields.Text()
    state = fields.Char()

    def submit(self):
        """ Prepare the Working Schedule feedback and trigger Approve. """
        self.ensure_one()
        hr_working = self.env['schedule.exchange'].browse(self._context.get('active_ids', []))
        hr_working.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            hr_working.action_approve()
        else:
            hr_working.action_refuse()
