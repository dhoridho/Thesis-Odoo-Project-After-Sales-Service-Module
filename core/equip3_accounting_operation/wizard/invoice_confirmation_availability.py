from odoo import models, fields
from odoo.tools.misc import get_lang

class ConfirmationWizard(models.TransientModel):
    _name = 'invoice.confirmation.availability'
    _description = 'Confirmation Wizard'

    message = fields.Text(string='Confirmation Message')
    invoice_id = fields.Many2one('account.move', string="Invoice")
    whatsapp = fields.Boolean(string="Whatsapp", Default=False)
    
    def confirm_action(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        if self.whatsapp == True:
            self.invoice_id.invoice_whatsapp(from_confirmation_wizard=True)
        else:
            self.invoice_id.action_invoice_sent(from_confirmation_wizard=True)