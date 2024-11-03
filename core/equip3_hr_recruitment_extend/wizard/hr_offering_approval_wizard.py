from odoo import fields, models, api


class HrOfferingRequestApprovalWizard(models.TransientModel):
    _name = 'hr.offering.request.approval.wizard'

    feedback = fields.Text()

    def submit(self):
        self.ensure_one()
        offering = self.env['hr.offering.request'].browse(self._context.get('active_ids', []))
        offering.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            offering.action_approve()
        else:
            offering.action_reject()
