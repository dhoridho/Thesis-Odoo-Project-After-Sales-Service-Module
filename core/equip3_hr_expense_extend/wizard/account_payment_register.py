# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    expense_sheet_id =  fields.Many2one('hr.expense.sheet', string='Expense Origin', invisible=True)

    @api.onchange('expense_sheet_id', 'journal_id')
    def _onchange_expense_sheet_id(self):
        for wizard in self:
            if wizard.expense_sheet_id and wizard.expense_sheet_id.cash_advance_amount < wizard.amount:
                wizard.amount = wizard.expense_sheet_id.cash_advance_amount

    def _create_payments(self):
        payments = super(AccountPaymentRegister, self)._create_payments()

        expense_sheets = self.env['hr.expense.sheet'].search([('account_move_id', 'in', self.line_ids.move_id.ids)])
        for expense_sheet in expense_sheets:
            if expense_sheet.currency_id.is_zero(expense_sheet.amount_residual):
                expense_sheet.state = 'done'
        return payments

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_approved_rp(self):
        super(AccountPayment, self).action_approved_rp()
        for rec in self:
            inv = self.env['account.move'].search([('name', '=', rec.ref)])
            if inv:
                expense_sheets = self.env['hr.expense.sheet'].search([('account_move_id', 'in', inv.ids)])
                for expense_sheet in expense_sheets:
                    if expense_sheet.currency_id.is_zero(expense_sheet.amount_residual):
                        expense_sheet.state = 'done'
