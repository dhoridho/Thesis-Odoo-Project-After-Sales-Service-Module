# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    branch_id = fields.Many2one('res.branch', string='Branch')
