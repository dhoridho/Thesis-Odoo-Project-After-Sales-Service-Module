# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class account_bank_statement_line(models.Model):
    _inherit = 'account.bank.statement.line'

    branch_id = fields.Many2one('res.branch', string='Branch')
