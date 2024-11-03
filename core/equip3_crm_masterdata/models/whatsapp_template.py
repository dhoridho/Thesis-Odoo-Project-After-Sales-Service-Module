from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class WhatsappTemplate(models.Model):
    _name = 'whatsapp.template'
    _description = "Whatsapp Template"

    name = fields.Char(string='Template Name', required=True)
    message = fields.Text(string='Message Content')
    is_default = fields.Boolean(string='Default Template')

    @api.constrains('is_default')
    def _check_default(self):
        checked_default = self.search([('id', '!=', self.id),('is_default', '=', True)], limit=1)  
        if self.is_default and checked_default:
            raise ValidationError("You cannot select more than one default message template!")