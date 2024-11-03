from odoo import api, fields, models, _
from odoo.exceptions import Warning


class AgreementStage(models.Model):
    _inherit = 'agreement.stage'

    is_editable = fields.Boolean(string='Editable', default=True)
    is_new_version = fields.Boolean(string='New Version', default=False)
    is_recurring_invoice = fields.Boolean(string='Recurring Invoice', default=False)
    is_non_recurring_invoice = fields.Boolean(string='Non-Recurring Invoice', default=False)
    
    @api.onchange('is_recurring_invoice')
    def onchange_is_recurring_invoice(self):
        if self.is_recurring_invoice == True:
            stage = self.env['agreement.stage'].search([('is_recurring_invoice', '=', True), ('id', '!=', self.ids)])
            if stage:
                raise Warning(_('Only one active Recurring Invoice toggle button is allowed.'))
    
    @api.onchange('is_non_recurring_invoice')
    def onchange_is_non_recurring_invoice(self):
        if self.is_non_recurring_invoice == True:
            stage = self.env['agreement.stage'].search([('is_non_recurring_invoice', '=', True), ('id', '!=', self.ids)])
            if stage:
                raise Warning( _('Only one active Non-Recurring Invoice toggle button is allowed.'))
    
    
