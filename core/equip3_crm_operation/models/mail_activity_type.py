
from odoo import models, fields

class MailActivityType(models.Model):
    _inherit = 'mail.activity.type'
    
    attachment_required = fields.Boolean(string="Attachment Required")