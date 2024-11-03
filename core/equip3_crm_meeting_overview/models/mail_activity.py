import logging

from odoo import api, exceptions, fields, models, _

_logger = logging.getLogger(__name__)

class MailActivity(models.Model):
    """ An actual activity to perform. Activities are linked to
    documents using res_id and res_model_id fields. Activities have a deadline
    that can be used in kanban view to display a status. Once done activities
    are unlinked and a message is posted. This message has a new activity_type_id
    field that indicates the activity linked to the message. """
    _inherit = 'mail.activity'

    def _action_done(self, feedback=False, attachment_ids=None):
        if self.res_model == 'crm.lead':
            lead_id = self.env[self.res_model].browse(self.res_id)
            lead_id.last_follow_up = self.date_deadline
        res = super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)
        return res