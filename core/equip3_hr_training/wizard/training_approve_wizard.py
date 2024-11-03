from odoo import fields, models, api


class TrainingRequestWizard(models.TransientModel):
    _name = 'training.request.wizard'

    feedback = fields.Text()
    is_reject = fields.Boolean(default=False)

    def submit(self):
        """ Prepare the training feedback and trigger Approve. """
        self.ensure_one()
        training_req = self.env['training.request'].browse(self._context.get('active_ids', []))
        training_req.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            training_req.action_approve()
        else:
             training_req.action_reject()
 


class TrainingConductWizard(models.TransientModel):
    _name = 'training.conduct.wizard'

    feedback = fields.Text()
    is_reject = fields.Boolean(default=False)

    def submit(self):
        """ Prepare the training feedback and trigger Approve. """
        self.ensure_one()
        training_req = self.env['training.conduct'].browse(self._context.get('active_ids', []))
        training_req.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            training_req.action_approve()
        else:
             training_req.action_reject()
