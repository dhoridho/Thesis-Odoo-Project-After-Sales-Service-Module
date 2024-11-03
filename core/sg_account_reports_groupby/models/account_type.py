from odoo import fields, models


class AccountAccountType(models.Model):
    _inherit = "account.account.type"
    _description = "Account Type"
    _order = "sequence"

    sequence = fields.Integer('Sequence')
