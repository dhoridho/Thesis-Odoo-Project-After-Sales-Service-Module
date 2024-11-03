from odoo import fields, models, api


class TrainingCancelRequestWizard(models.TransientModel):
    _name = 'training.cancel.request.wizard'

    feedback = fields.Text()
    is_reject = fields.Boolean(default=False)

    def submit(self):
        """ Prepare the training cancel feedback and trigger Approve. """
        self.ensure_one()
        training_cancel = self.env['hr.training.cancellation'].browse(self._context.get('active_ids', []))
        training_cancel.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            training_cancel.action_approve()
        else:
             training_cancel.action_reject()

class TrainingConductCancelRequestWizard(models.TransientModel):
    _name = 'training.conduct.cancel.request.wizard'

    feedback = fields.Text()
    is_reject = fields.Boolean(default=False)

    def submit(self):
        """ Prepare the training conduct cancel feedback and trigger Approve. """
        self.ensure_one()
        training_conduct_cancel = self.env['hr.training.conduct.cancellation'].browse(self._context.get('active_ids', []))
        training_conduct_cancel.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            training_conduct_cancel.action_approve()
        else:
             training_conduct_cancel.action_reject()