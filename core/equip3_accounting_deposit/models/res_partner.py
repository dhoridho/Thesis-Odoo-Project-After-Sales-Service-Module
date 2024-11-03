from odoo import models, fields, api, _


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"


    is_vendor = fields.Boolean(string='Vendor')