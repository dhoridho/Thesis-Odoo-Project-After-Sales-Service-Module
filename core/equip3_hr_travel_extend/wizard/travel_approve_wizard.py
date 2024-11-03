from odoo import fields, models, api



class TravelRequestWizard(models.TransientModel):
    _name = 'travel.request.wizard'

    feedback = fields.Text()
    is_reject = fields.Boolean(default=False)
    

    def submit(self):
        """ Prepare the Travel feedback and trigger Approve. """
        self.ensure_one()
        travel_req = self.env['travel.request'].browse(self._context.get('active_ids', []))
        travel_req.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            travel_req.action_approve()
        else:
             travel_req.action_reject()

