# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountBankStatementLineWizard(models.TransientModel):
    _name = "account.bank.statement.line.wizard"
    _description = "Account Bank Statement Line Wizard"

    
    def asset_compute(self):
        statement_line_obj = self.env['account.bank.statement.line']
        domain = statement_line_obj.scheduler_queue_generate_bank_statement_journal()
        return {
            'name': _('Generate Bank Statement Journal'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.bank.statement.line',
            'view_id': False,
            'domain' : [('id','in',domain)],
            'type': 'ir.actions.act_window',
        }