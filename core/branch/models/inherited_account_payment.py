# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    branch_id = fields.Many2one('res.branch', string='Branch')
