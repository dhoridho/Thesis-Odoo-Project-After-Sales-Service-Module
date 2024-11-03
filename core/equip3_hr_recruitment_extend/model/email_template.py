import werkzeug
from odoo import fields, models, api


class hashMicroInheritEmailTemplates(models.Model):
    _inherit = 'mail.template'

    qualification_url = fields.Char('Qualification URL')
    is_digital_flag = fields.Boolean('Digital Flag',default=False)

