# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ReturnDepositWizard(models.TransientModel):
    _name = 'account.deposit.return'
    _description = 'Return Deposit Wizard'

    return_date = fields.Date(string='Date', default=fields.Date.context_today)
    return_amount = fields.Float(string='Amount', digits=0, required=True)
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True,
                                 domain=[('type', 'in', ('bank', 'cash'))])
    payment_difference = fields.Float(string='Payment Difference', compute='_compute_payment_difference', readonly=True)
    payment_difference_handling = fields.Selection(
        [('open', 'Keep open'), ('reconcile', 'Mark Deposit as fully returned')], default='open',
        string="Payment Difference", copy=False)
    diff_amount_account_id = fields.Many2one('account.account', string='Post Difference In')
    remaining_amount = fields.Float(string="Remaining Amount")
    customer_deposit_id = fields.Many2one('customer.deposit', string="Customer Deposit")
    vendor_deposit_id = fields.Many2one('vendor.deposit', string="Vendor Deposit")

    @api.depends('return_amount', 'remaining_amount')
    def _compute_payment_difference(self):
        for record in self:
            record.payment_difference = record.remaining_amount - record.return_amount

    def return_deposit(self):
        if self.return_amount > self.remaining_amount:
            raise ValidationError("Please input amount less than %d" % (self.remaining_amount))
        elif self.return_amount <= self.remaining_amount and self.customer_deposit_id:
            customer_deposit_id = self.customer_deposit_id
            name = 'Return Deposit ' + (customer_deposit_id.name or '')
            ref = name
            currency_rate = self.env['res.currency'].search([('id', '=', customer_deposit_id.currency_id.id)], limit=1).rate
            vals = {
                'ref': ref,
                'partner_id': customer_deposit_id.partner_id.id,
                'date': self.return_date,
                'journal_id': self.journal_id.id,
                'branch_id': customer_deposit_id.branch_id.id,
                'analytic_group_ids': [(6, 0, customer_deposit_id.analytic_group_ids.ids)],
                
            }
            if self.payment_difference == 0 or self.payment_difference_handling == 'open':
                debit_vals = {
                    'debit': abs(self.return_amount / currency_rate) if customer_deposit_id.currency_id else abs(self.return_amount),
                    'date': self.return_date,
                    'name': name,
                    'partner_id': customer_deposit_id.partner_id.id,
                    'credit': 0.0,
                    'account_id': customer_deposit_id.deposit_account_id.id,
                    'analytic_tag_ids': [(6, 0, customer_deposit_id.analytic_group_ids.ids)],
                }
                credit_vals = {
                    'debit': 0.0,
                    'date': self.return_date,
                    'name': name,
                    'partner_id': customer_deposit_id.partner_id.id,
                    'credit': abs(self.return_amount / currency_rate) if customer_deposit_id.currency_id else abs(self.return_amount),
                    'account_id': self.journal_id.payment_credit_account_id.id,
                    'analytic_tag_ids': [(6, 0, customer_deposit_id.analytic_group_ids.ids)],
                }
                vals.update({'line_ids': [(0, 0, credit_vals), (0, 0, debit_vals)]})
                move_id = self.env['account.move'].create(vals)
                move_id.post()
                if self.payment_difference == 0:
                    customer_deposit_id.write({
                        'state': 'returned',
                        'return_deposit': move_id.id
                    })
                else:
                    customer_deposit_id.deposit_return_ids += move_id
            elif self.payment_difference_handling == 'reconcile':
                debit_vals = {
                    'debit': abs(customer_deposit_id.remaining_amount / currency_rate) if customer_deposit_id.currency_id else abs(customer_deposit_id.remaining_amount),
                    'date': self.return_date,
                    'name': name,
                    'partner_id': customer_deposit_id.partner_id.id,
                    'credit': 0.0,
                    'account_id': customer_deposit_id.deposit_account_id.id,
                    'analytic_tag_ids': [(6, 0, customer_deposit_id.analytic_group_ids.ids)],
                }
                credit_vals = {
                    'debit': 0.0,
                    'date': self.return_date,
                    'name': name,
                    'partner_id': customer_deposit_id.partner_id.id,
                    'credit': abs(self.return_amount / currency_rate) if customer_deposit_id.currency_id else abs(self.return_amount),
                    'account_id': self.journal_id.payment_credit_account_id.id,
                    'analytic_tag_ids': [(6, 0, customer_deposit_id.analytic_group_ids.ids)],
                }
                credit_vals_1 = {
                    'debit': 0.0,
                    'date': self.return_date,
                    'name': name,
                    'partner_id': customer_deposit_id.partner_id.id,
                    'credit': abs(self.payment_difference / currency_rate) if customer_deposit_id.currency_id else abs(self.payment_difference),
                    'account_id': self.diff_amount_account_id.id,
                    'analytic_tag_ids': [(6, 0, customer_deposit_id.analytic_group_ids.ids)],
                }
                vals['line_ids'] = [(0, 0, credit_vals), (0, 0, credit_vals_1), (0, 0, debit_vals)]
                move_id = self.env['account.move'].create(vals)
                move_id.post()
                customer_deposit_id.write({
                    'state': 'returned',
                    'return_deposit': move_id.id
                })
        elif self.return_amount <= self.remaining_amount and self.vendor_deposit_id:
            vendor_deposit_id = self.vendor_deposit_id
            name = 'Return Deposit ' + (vendor_deposit_id.name or '')
            ref = name
            currency_rate = self.env['res.currency'].search([('id', '=', vendor_deposit_id.currency_id.id)], limit=1).rate
            vals = {
                'ref': ref,
                'partner_id': vendor_deposit_id.partner_id.id,
                'date': self.return_date,
                'journal_id': self.journal_id.id,
                'branch_id': vendor_deposit_id.branch_id.id,
                'analytic_group_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
            }
            if self.payment_difference == 0 or \
                    self.payment_difference_handling == 'open':
                debit_vals = {
                    'debit': abs(self.return_amount / currency_rate) if vendor_deposit_id.currency_id else abs(self.return_amount),
                    'date': self.return_date,
                    'name': name,
                    'partner_id': vendor_deposit_id.partner_id.id,
                    'credit': 0.0,
                    'account_id': self.journal_id.payment_debit_account_id.id,
                    'analytic_tag_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
                }
                credit_vals = {
                    'debit': 0.0,
                    'date': self.return_date,
                    'name': name,
                    'partner_id': vendor_deposit_id.partner_id.id,
                    'credit': abs(self.return_amount / currency_rate) if vendor_deposit_id.currency_id else abs(self.return_amount),
                    'account_id': vendor_deposit_id.deposit_account_id.id,
                    'analytic_tag_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
                }
                vals.update({'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]})
                move_id = self.env['account.move'].create(vals)
                move_id.post()
                if self.payment_difference == 0:
                    vendor_deposit_id.write({
                        'state': 'returned',
                        'return_deposit': move_id.id
                    })
                else:
                    vendor_deposit_id.deposit_return_ids += move_id
            elif self.payment_difference_handling == 'reconcile':
                debit_vals = {
                    'debit': abs(self.return_amount / currency_rate) if vendor_deposit_id.currency_id else abs(self.return_amount),
                    'date': self.return_date,
                    'name': name,
                    'partner_id': vendor_deposit_id.partner_id.id,
                    'credit': 0.0,
                    'account_id': self.journal_id.payment_debit_account_id.id,
                    'analytic_tag_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
                }
                debit_vals_1 = {
                    'debit': abs(self.payment_difference /currency_rate) if vendor_deposit_id.currency_id else abs(self.payment_difference),
                    'date': self.return_date,
                    'name': name,
                    'partner_id': vendor_deposit_id.partner_id.id,
                    'credit': 0.0,
                    'account_id': self.diff_amount_account_id.id,
                    'analytic_tag_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
                }
                credit_vals = {
                    'debit': 0.0,
                    'date': self.return_date,
                    'name': name,
                    'partner_id': vendor_deposit_id.partner_id.id,
                    'credit': abs(self.return_amount / currency_rate) if vendor_deposit_id.currency_id else abs(self.return_amount),
                    'account_id': vendor_deposit_id.deposit_account_id.id,
                    'analytic_tag_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
                }
                vals['line_ids'] = [(0, 0, debit_vals), (0, 0, debit_vals_1), (0, 0, credit_vals)]
                move_id = self.env['account.move'].create(vals)
                move_id.post()
                vendor_deposit_id.write({
                    'state': 'returned',
                    'return_deposit': move_id.id
                })

    @api.model
    def default_get(self, vals):
        res = super(ReturnDepositWizard, self).default_get(vals)
        context = dict(self.env.context) or {}
        if context.get('active_model') == 'customer.deposit':
            deposit_id = self.env['customer.deposit'].browse(self._context.get('active_id'))
            res['remaining_amount'] = deposit_id.remaining_amount
            res['customer_deposit_id'] = deposit_id.id
            res['return_amount'] = deposit_id.remaining_amount
        elif context.get('active_model') == 'vendor.deposit':
            ven_deposit_id = self.env['vendor.deposit'].browse(self._context.get('active_id'))
            res['remaining_amount'] = ven_deposit_id.remaining_amount
            res['vendor_deposit_id'] = ven_deposit_id.id
            res['return_amount'] = ven_deposit_id.remaining_amount
        return res
