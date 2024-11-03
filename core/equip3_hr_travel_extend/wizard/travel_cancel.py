from odoo import fields, models, api


class TravelCancelWizard(models.TransientModel):
    _name = 'travel.cancel.wizard'

    feedback = fields.Text()
    is_reject = fields.Boolean(default=False)

    def submit(self):
        """ Prepare the Travel feedback and trigger Approve. """
        self.ensure_one()
        travel_cancel = self.env['employee.travel.cancellation'].browse(self._context.get('active_ids', []))
        travel_cancel.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            travel_cancel.action_approve()
        else:
             travel_cancel.action_reject()