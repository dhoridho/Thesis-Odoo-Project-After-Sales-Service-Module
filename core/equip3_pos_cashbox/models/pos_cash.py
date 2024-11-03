# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosCashInOut(models.Model):
    _name = 'pos.cash.in.out'
    _description = "Pos Cash In Out"
    _rec_name = 'action'

    action = fields.Selection([
        ('in', 'Put Money In'),
        ('out', 'Take Money Out'),
    ], string='Action')
    product_id = fields.Many2one('product.product', string='Product Service', domain="[('is_for_cash_management','=',True)]")
    amount = fields.Float(string='Amount', digits=0)
    reason = fields.Char('Reason')
    pos_session_id = fields.Many2one('pos.session', string='POS Session')
    account_move_id = fields.Many2one('account.move', string='Journal Entry')
    

    def _prepare_journal_for_cash_management(self):
        self.ensure_one()
        line_ids, first_vals, second_vals = [], [], []
        session = self.pos_session_id

        if not session.config_id.cashbox_payment_method_id:
            raise ValidationError(_('Please setup Cashbox Payment Method in the config'))
        if not self.product_id.property_account_income_id:
            raise ValidationError(_('Please configure Income Account in product "%s"' % self.product_id.name ))
        if not self.product_id.property_account_expense_id:
            raise ValidationError(_('Please configure Expense Account in product "%s"' % self.product_id.name ))

        journal_id = session.config_id.cashbox_payment_method_id.cash_journal_id
        intermediary_account_id = session.config_id.cashbox_payment_method_id.receivable_account_id
        property_account_income_id = self.product_id.property_account_income_id
        property_account_expense_id = self.product_id.property_account_expense_id
        ref = 'Cashbox %s - ' % str(session.name)
        if self.action == 'in':
            ref += 'Put Money In'
            first_vals = {
                'debit' : 0, 
                'credit' : self.amount, 
                'name' : 'Income - %s' % self.product_id.name, 
                'account_id' : property_account_income_id.id,
                'currency_id' : session.currency_id.id,
                'company_id' : session.company_id.id,
            }
            second_vals = {
                'debit' : self.amount, 
                'credit' : 0, 
                'name' : 'Cashbox Intermediary', 
                'account_id' : intermediary_account_id.id,
                'currency_id' : session.currency_id.id,
                'company_id' : session.company_id.id,
            }

        if self.action == 'out':
            ref += 'Take Money Out'
            first_vals = {
                'debit' : self.amount, 
                'credit' : 0, 
                'name' : 'Expense - %s' % self.product_id.name, 
                'account_id' : property_account_expense_id.id,
                'currency_id' : session.currency_id.id,
                'company_id' : session.company_id.id,
            }
            second_vals = {
                'debit' : 0, 
                'credit' : self.amount, 
                'name' : 'Cashbox Intermediary', 
                'account_id' : intermediary_account_id.id,
                'currency_id' : session.currency_id.id,
                'company_id' : session.company_id.id,
            }

        move_vals = {
            'is_from_pos_cash_management': True,
            'move_type': 'entry',
            'ref': ref,
            'origin': 'Cashbox ' + session.name,
            'pos_session_id': session.id,
            'journal_id': journal_id.id,
            'line_ids': [(0, 0, first_vals), (0, 0, second_vals)],
        }
        return move_vals


class PosCashInOut(models.Model):
    _name = 'pos.cashbox.history'
    _description = "Pos Cashbox History"
    _rec_name = 'pos_session_id'
    _order = 'create_date desc'

    start_balance = fields.Float(string='Start balance', digits=0)
    closing_balance = fields.Float(string='Closing balance', digits=0)
    opened_by_user_id = fields.Many2one('res.users', 'Opened By')
    pos_session_id = fields.Many2one('pos.session', string='Session')
    pos_config_id = fields.Many2one('pos.config', string='Poinf of Sale')
    start_date = fields.Datetime(string='Start Date')
    closing_date = fields.Datetime(string='Closing Date')


    def save_balance_history(self, session):
        History = self.env['pos.cashbox.history']
        domain = [('pos_session_id','=', session.id)]
        history = self.env['pos.cashbox.history'].search(domain, limit=1)
        if history:
            history.write({ 
                'start_balance': session.cash_opening_balance,
                'closing_balance': session.cash_closing_balance,
            })
        else:
            return History.create({
                'start_balance': session.cash_opening_balance,
                'closing_balance': session.cash_closing_balance,
                'opened_by_user_id': session.user_id.id,
                'pos_session_id': session.id,
                'pos_config_id': session.config_id.id,
            })
        return history

