
import logging
import re
import werkzeug

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

class SurveyInvite(models.TransientModel):
    _inherit = 'survey.invite'
    @api.model
    def _get_default_from(self):
        if self.env.user.email:
            return tools.formataddr((self.env.user.name, self.env.user.email))
        if not self.env.user.email:
            return "mail@hashmicro.com"
        raise UserError(_("Unable to post message"))
    
    email_from = fields.Char('From', default=_get_default_from, help="Email address of the sender.")

   