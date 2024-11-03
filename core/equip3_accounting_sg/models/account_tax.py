
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def action_remove_taxes(self):
        self.env['account.tax'].search(
            [('description', 'in', ['ST1', 'PT1', 'ST0', 'PT0', 'ST2', 'PT2'])]
        ).write({'active': False})
