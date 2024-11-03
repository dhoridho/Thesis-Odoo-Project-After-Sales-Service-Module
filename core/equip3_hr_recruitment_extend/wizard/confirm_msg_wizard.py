from odoo import models, fields, api


class SendEmailPopupWizard(models.TransientModel):
    _name = 'send.email.popup.wizard'
    _description = 'Send Email Popup Wizard'

    message = fields.Text(string='Message', readonly=True, default="The Offering Letters have been sent to the respective applicants.")