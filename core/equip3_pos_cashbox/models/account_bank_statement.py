# -*- coding: utf-8 -*-

from odoo import api, fields, models

class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    transaction = fields.Float(string='Transaction', digits=0)
    journal_entries_status = fields.Selection([
        ('Journal Entries Posted', 'Journal Entries Posted'),
        ('Cannot create Journal Entries', 'Cannot create Journal Entries'),
    ], string='Journal Entries Status')

    def _compute_starting_balance(self):
        super(AccountBankStatement, self)._compute_starting_balance()
        for statement in self:
            if statement.pos_session_id:
                session = statement.pos_session_id
                statement.balance_start = session.cash_opening_balance

    def _compute_ending_balance(self):
        super(AccountBankStatement, self)._compute_ending_balance()
        for statement in self:
            if statement.pos_session_id:
                session = statement.pos_session_id
                statement.balance_end_real = session.cash_register_balance_end_real