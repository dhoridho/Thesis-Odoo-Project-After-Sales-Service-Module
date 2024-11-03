from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    bom_tools = fields.Boolean(string='Tools')
