# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ReturnDepositWizard(models.TransientModel):
    _inherit = 'account.deposit.return'

    def return_cash_advance(self):
        if self.return_amount > self.remaining_amount:
            raise ValidationError("Please input amount less than %d" % (self.remaining_amount))
        vendor_deposit_id = self.vendor_deposit_id
        ref = 'Return Cash Advance ' + (vendor_deposit_id.communication or '')
        name = 'Return Cash Advance ' + (vendor_deposit_id.name or '')
        vals = {
            'ref': ref,
            'date': self.return_date,
            'journal_id': self.journal_id.id,
            'branch_id': vendor_deposit_id.branch_id.id,
        }
        if self.payment_difference == 0 or \
           self.payment_difference_handling == 'open':
            debit_vals = {
                    'debit': abs(self.return_amount),
                    'date': self.return_date,
                    'name': name,
                    'credit': 0.0,
                    'account_id': self.journal_id.payment_debit_account_id.id,
                }
            credit_vals = {
                    'debit': 0.0,
                    'date': self.return_date,
                    'name': name,
                    'credit': abs(self.return_amount),
                    'account_id': vendor_deposit_id.deposit_account_id.id,
                }
            vals.update({'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]})
            move_id = self.env['account.move'].create(vals)
            vendor_deposit_id.return_cash_advance_ids = [(4, move_id.id)]
            move_id.post()
            if self.payment_difference == 0:
                vendor_deposit_id.write({
                    'remaining_amount': 0,
                    'state': 'returned'
                })
            elif self.payment_difference_handling == 'open' and \
                self.payment_difference != 0:
                vendor_deposit_id.write({
                    'remaining_amount': self.remaining_amount - self.return_amount,
                })
        elif self.payment_difference_handling == 'reconcile':
            debit_vals = {
                    'debit': abs(self.return_amount),
                    'date': self.return_date,
                    'name': name,
                    'credit': 0.0,
                    'account_id': self.journal_id.payment_debit_account_id.id,
                }
            debit_vals_1 = {
                    'debit': abs(self.payment_difference),
                    'date': self.return_date,
                    'name': name,
                    'credit': 0.0,
                    'account_id': self.diff_amount_account_id.id,
                }
            credit_vals = {
                    'debit': 0.0,
                    'date': self.return_date,
                    'name': name,
                    'credit': abs(vendor_deposit_id.remaining_amount),
                    'account_id': vendor_deposit_id.deposit_account_id.id,
                }
            vals['line_ids'] = [(0, 0, debit_vals), (0, 0, debit_vals_1), (0, 0, credit_vals)]
            move_id = self.env['account.move'].create(vals)
            vendor_deposit_id.return_cash_advance_ids = [(4, move_id.id)]
            move_id.post()
            vendor_deposit_id.write({
                'remaining_amount': 0,
                'state': 'returned'
            })