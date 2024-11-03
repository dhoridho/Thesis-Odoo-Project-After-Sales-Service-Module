from odoo import fields, models, api


class HrAppraisalWizard(models.TransientModel):
    _name = 'hr.appraisal.wizard'

    feedback = fields.Text()

    def submit(self):
        """ Prepare the Appraisal feedback and trigger Approve. """
        self.ensure_one()
        hr_appraisal = self.env['employee.performance'].browse(self._context.get('active_ids', []))
        hr_appraisal.feedback_parent = self.feedback
        hr_appraisal.action_done()
