# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ConvertToRevenue(models.TransientModel):
    _name = 'convert.revenue'
    _description = 'Convert to Revenue Wizard'

    date = fields.Date(string='Date', default=fields.Date.context_today)
    revenue_account_id = fields.Many2one('account.account', "Revenue Account")
    deposit_type = fields.Selection([('customer_deposit', 'Customer Deposit'), ('vendor_deposit', 'Vendor Deposit')], string='Deposit Type')

    def action_confirm(self):
        if self.deposit_type == "customer_deposit":
            deposit_id = self.env['customer.deposit'].browse(self._context.get('active_ids'))
            ref = 'Convert to Revenue ' + (deposit_id.name or '')
            name = ref
            currency_rate = self.env['res.currency'].search([('id', '=', deposit_id.currency_id.id)], limit=1).rate
            debit_vals = {
                    'name': ref,
                    'partner_id': deposit_id.partner_id.id,
                    'credit': 0.0,
                    'date': self.date,
                    'debit': deposit_id.remaining_amount / currency_rate if deposit_id.currency_id else deposit_id.remaining_amount ,
                    'account_id': deposit_id.deposit_account_id.id,
                    'analytic_tag_ids': [(6, 0, deposit_id.analytic_group_ids.ids)],
                }
            credit_vals = {
                    'name': ref,
                    'partner_id': deposit_id.partner_id.id,
                    'debit': 0.0,
                    'date': self.date,
                    'credit': deposit_id.remaining_amount / currency_rate if deposit_id.currency_id else deposit_id.remaining_amount ,
                    'account_id': self.revenue_account_id.id,
                    'analytic_tag_ids': [(6, 0, deposit_id.analytic_group_ids.ids)],
                }
            data = {
                'ref' : name,
                'partner_id': deposit_id.partner_id.id,
                'date' : self.date,
                'journal_id' : deposit_id.deposit_reconcile_journal_id.id,
                'analytic_group_ids': [(6, 0, deposit_id.analytic_group_ids.ids)],
                'branch_id' : deposit_id.branch_id.id,
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move_id = self.env['account.move'].create(data)
            move_id.post()
            deposit_id.write({'state' : 'converted', 'convert_to_revenue_move_id': move_id.id})
        elif self.deposit_type == "vendor_deposit":
            deposit_id = self.env['vendor.deposit'].browse(self._context.get('active_ids'))
            ref = 'Convert to Expense ' + (deposit_id.name or '')
            name = ref
            currency_rate = self.env['res.currency'].search([('id', '=', deposit_id.currency_id.id)], limit=1).rate
            debit_vals = {
                    'name': ref,
                    'partner_id': deposit_id.partner_id.id,
                    'credit': 0.0,
                    'date': self.date,
                    'debit': deposit_id.remaining_amount / currency_rate if deposit_id.currency_id else deposit_id.remaining_amount ,
                    'account_id': self.revenue_account_id.id,
                    'analytic_tag_ids': [(6, 0, deposit_id.analytic_group_ids.ids)],
                }
            credit_vals = {
                    'name': ref,
                    'partner_id': deposit_id.partner_id.id,
                    'debit': 0.0,
                    'date': self.date,
                    'credit': deposit_id.remaining_amount / currency_rate if deposit_id.currency_id else deposit_id.remaining_amount ,
                    'account_id': deposit_id.deposit_account_id.id,
                    'analytic_tag_ids': [(6, 0, deposit_id.analytic_group_ids.ids)],
                }
            data = {
                'ref' : name,
                'partner_id': deposit_id.partner_id.id,
                'date' : self.date,
                'journal_id' : deposit_id.deposit_reconcile_journal_id.id,
                'analytic_group_ids': [(6, 0, deposit_id.analytic_group_ids.ids)],
                'branch_id' : deposit_id.branch_id.id,
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move_id = self.env['account.move'].create(data)
            move_id.post()
            deposit_id.write({'state' : 'converted', 'convert_to_expense_move_id': move_id.id})