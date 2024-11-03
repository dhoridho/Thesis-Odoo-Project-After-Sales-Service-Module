from odoo import api , fields , models


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    project_invoice = fields.Boolean(string="Project Invoice", default=False)