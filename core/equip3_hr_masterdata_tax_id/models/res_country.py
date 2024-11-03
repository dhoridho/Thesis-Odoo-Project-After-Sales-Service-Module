from odoo import _, api, fields, models

class ResCountryInherit(models.Model):
    _inherit = 'res.country'

    tax_treaty_rate = fields.Float("Tax Treaty Rate (%)")