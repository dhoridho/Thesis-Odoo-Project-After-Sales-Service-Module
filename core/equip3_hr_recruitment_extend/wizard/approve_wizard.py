from odoo import fields, models, api


class HrManPlanWizard(models.TransientModel):
    _name = 'hr.man.plan.wizard'

    feedback = fields.Text()
    state = fields.Char()

    def submit(self):
        """ Prepare the Loan feedback and trigger Approve. """
        self.ensure_one()
        man_plan = self.env['manpower.planning'].browse(self._context.get('active_ids', []))
        man_plan.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            man_plan.action_approve()
        else:
             man_plan.action_to_reject()
