from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RestCompany(models.Model):
    _inherit = 'res.company'
    
    privy_id = fields.Char()
    