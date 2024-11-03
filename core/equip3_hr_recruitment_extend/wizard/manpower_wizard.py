from odoo import fields, models, api


class ManpowerlWizard(models.TransientModel):
    _name = 'manpower.wizard'

    feedback = fields.Text()

    def submit(self):
        """ Prepare the Manpower Requisition feedback and trigger Approve. """
        self.ensure_one()
        mpp = self.env['manpower.requisition'].browse(self._context.get('active_ids', []))
        mpp.feedback_parent = self.feedback
        mpp.action_done()
