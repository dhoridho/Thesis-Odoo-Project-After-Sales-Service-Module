# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ReconcileVendorDepositWizard(models.TransientModel):
    _name = 'account.vendor.deposit.reconcile'

    date = fields.Date(string='Date', default=fields.Date.context_today)
    allocation_line_ids = fields.One2many('vendor.deposit.line.reconcile', 'deposit_reconcile_id', string="Invoice Deposit")

    @api.model
    def calculate_amount(self, amount, src_currency, company_currency, invoice_currency=False):
        amount_currency = False
        currency_id = False
        if src_currency and src_currency != company_currency:
            amount_currency = amount
            amount = src_currency.with_context(self._context).compute(amount, company_currency)
            currency_id = src_currency.id
        if invoice_currency and invoice_currency != company_currency and not amount_currency:
            amount_currency = src_currency.with_context(self._context).compute(amount, invoice_currency)
            currency_id = invoice_currency.id
        return amount, amount_currency, currency_id

    def reconcile_deposit(self):
        move_obj        = self.env['account.move']
        move_line_obj   = self.env['account.move.line']
        vendor_deposit_id = self.env['vendor.deposit'].search([('id','=',self.env.context.get('active_id'))])
        if vendor_deposit_id:
            #Check Total Remaining
            total_remaining = vendor_deposit_id.remaining_amount
            total_amount_to_reconcile = sum(l.allocation_amount for l in self.allocation_line_ids)
            total_allocation_amount = 0

            if total_amount_to_reconcile > total_remaining:
                raise ValidationError(_('Total Allocation can not bigger than Remaining Amount'))
            
            for alloc in self.allocation_line_ids:
                invline_to_reconcile = self.env['account.move.line']
                depositline_to_reconcile = self.env['account.move.line']
                #Create Recon Deposit Journal
                line_ids = []
                vendor_deposit_id.invoice_deposit_ids = [(4, alloc.invoice_id.id)]
                total_allocation_amount += alloc.allocation_amount
                amount, amount_currency, currency_id = self.with_context(date=self.date).calculate_amount(alloc.allocation_amount, vendor_deposit_id.currency_id, vendor_deposit_id.company_id.currency_id, alloc.invoice_id.currency_id)
                if vendor_deposit_id.currency_id != alloc.invoice_id.currency_id:
                    allocation_amount = vendor_deposit_id.currency_id.with_context(date=alloc.invoice_id.date).compute(alloc.allocation_amount, alloc.invoice_id.currency_id)
                else:
                    allocation_amount = alloc.invoice_id.amount_residual
                if allocation_amount > alloc.invoice_id.amount_residual:
                    raise UserError(_('Total Allocation can not bigger than Amount Due of Invoice. Invoice NO. %s') % alloc.invoice_id.number)

                move_line_db = {
                        'name'      : 'Deposit Reconcile',
                        'analytic_tag_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
                        'account_id': vendor_deposit_id.deposit_account_id.id,
                        'debit'     : 0,
                        'credit'    : amount ,
                        'partner_id': vendor_deposit_id.partner_id.id,
                        'currency_id': vendor_deposit_id.currency_id.id,
                        'amount_currency': -amount_currency,
                    }

                line_ids.append((0,0,move_line_db))
                move_line_cr = {
                        'name'      : 'Deposit Reconcile',
                        'analytic_tag_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
                        'account_id': vendor_deposit_id.partner_id.property_account_payable_id.id,
                        'debit'     : amount  ,
                        'credit'    : 0,
                        'partner_id': vendor_deposit_id.partner_id.id,
                        'currency_id': vendor_deposit_id.currency_id.id,
                        'amount_currency': amount_currency,
                    }
                line_ids.append((0,0,move_line_cr))
                
                move_vals = {
                             'journal_id'    : vendor_deposit_id.deposit_reconcile_journal_id.id,
                             'analytic_group_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
                             'date'          : self.date,
                             'partner_id': vendor_deposit_id.partner_id.id,
                             'ref'           : alloc.invoice_id.name,
                             'branch_id': vendor_deposit_id.branch_id.id,
                             'line_ids'      : line_ids,
                    }

                reconcile_move_deposit_id = move_obj.create(move_vals)
                vendor_deposit_id.reconcile_deposit_ids = [(4, reconcile_move_deposit_id.id)]
                reconcile_move_deposit_id.action_post()
                to_reconcile = alloc.invoice_id.line_ids.filtered(lambda r:r.account_id.id == vendor_deposit_id.partner_id.property_account_payable_id.id)
                domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                for lines in to_reconcile:
                    payment_lines = reconcile_move_deposit_id.line_ids.filtered_domain(domain)
                    for account in payment_lines.account_id:
                        (payment_lines + lines)\
                            .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                            .reconcile()

            if vendor_deposit_id.remaining_amount == 0.0:
                vendor_deposit_id.state = 'reconciled'
        return True

class VendorDepositLineWizard(models.TransientModel):
    _name = 'vendor.deposit.line.reconcile'

    @api.onchange('invoice_id')
    def onchange_invoice_id(self):
        self._get_move_vendor_deposit()
        if self.invoice_id:
            self.invoice_due_amount = self.invoice_id.amount_residual
            self.allocation_amount = self.invoice_id.amount_residual

    def _get_move_vendor_deposit(self):
        for record in self:
            inv_ids = []
            if self.env.context.get('active_id'):
                vendor_deposit_id = self.env['vendor.deposit'].search([('id','=',self.env.context.get('active_id'))])
                if vendor_deposit_id.partner_id.parent_id:
                    parent = vendor_deposit_id.partner_id.parent_id.ids + vendor_deposit_id.partner_id.parent_id.child_ids.ids
                if not vendor_deposit_id.partner_id.parent_id:
                    parent = vendor_deposit_id.partner_id.ids + vendor_deposit_id.partner_id.child_ids.ids 
                inv_ids = self.env['account.move'].search([('partner_id','in', parent), ('state','=','posted'), ('payment_state','in',('not_paid', 'partial')), ('journal_id.type','=','purchase'), ('move_type','=','in_invoice')]).ids
            record.filter_move_ids = [(6, 0, inv_ids)]

    deposit_reconcile_id = fields.Many2one('account.vendor.deposit.reconcile', string="Deposit Reconcile")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    filter_move_ids = fields.Many2many('account.move', compute='_get_move_vendor_deposit', store=False)
    allocation_amount = fields.Float(string='Allocation Amount')
    invoice_due_amount = fields.Float(string="Due Amount")
