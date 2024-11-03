
from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit = "res.partner"

    is_leads = fields.Boolean(string='Leads')
