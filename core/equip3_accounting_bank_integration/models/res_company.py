from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    bank_integrate_url = fields.Char(string='Middleware URL')
    bank_integrate_username = fields.Char(string='Username')
    bank_integrate_password = fields.Char(string='Password')
    validate_api = fields.Boolean()