from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    is_inverse_rate = fields.Boolean(
        string="Use Inverse Rate"
    )
    is_taxes_rate = fields.Boolean(
        string="Taxes have different exchange rate"
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_inverse_rate = fields.Boolean(
        related="company_id.is_inverse_rate", readonly=False)
    is_taxes_rate = fields.Boolean(
        related="company_id.is_taxes_rate", readonly=False)
