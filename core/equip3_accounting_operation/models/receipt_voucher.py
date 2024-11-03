# -*- coding: utf-8 -*-
from odoo import fields, models, api, _, tools
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, date, timedelta
from odoo.tools.misc import formatLang, format_date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import pytz
import logging

import requests
import json
import base64
from ast import literal_eval
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
from . import amount_to_text
try:
    from num2words import num2words
except ImportError:
    logging.getLogger(__name__).warning(
        "The num2words python library is not installed, l10n_mx_edi features won't be fully available.")
    num2words = None


_logger = logging.getLogger(__name__)


class ReceiptVoucher(models.Model):
    _name = "receipt.voucher"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Receipt Voucher"
    

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]
    
    @api.model
    def _domain_bank(self):
        active_company_id = self.env.company.id
        return [('company_id','=',active_company_id),('type','in',['bank','cash'])]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)
    create_by = fields.Many2one('res.users', string="Created By", default=lambda self: self.env.user)
    create_date = fields.Datetime(string="Created Date", default=fields.Datetime.now)
    
    payment_count = fields.Integer(compute='_get_payment_count')
    payment_ids = fields.One2many('account.payment', 'receipt_voucher_id', string="Payments")

    name = fields.Char(string="Name", required=True, copy=False, readonly=True, index=True, default='/')
    partner_id = fields.Many2one('res.partner', string="Payee Name", track_visibility='always')
    partner_ids = fields.Many2many('res.partner', 'receipt_voucher_partner_rel', 'receipt_voucher_id', 'partner_id', string="Payee Name", required=True, track_visibility='always')
    voucher_date = fields.Date(string="Voucher Date", required=True, default=fields.Date.context_today, track_visibility='always')
    bank_id = fields.Many2one('account.journal',domain=_domain_bank, string="Bank", required=True, track_visibility='always')
    cheque_number = fields.Char('Cheque Number')
    cheque_date = fields.Date('Cheque Date')
    # customer_invoice_ids = fields.Many2many('account.move', string="Customer Invoice", required=True, track_visibility='always', domain="[('id', 'in', customer_allowed_ids)], ")
    customer_invoice_ids = fields.Many2many('account.move', string="Customer Invoice", required=True, domain="[('id', 'in', customer_allowed_ids), ('payment_state', '!=', 'paid'), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]", track_visibility='always')
    currency_id = fields.Many2one('res.currency', string="Currency", required=True, default=lambda self: self.env.company.currency_id)
    remarks = fields.Text('Remarks')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company)
    # branch_id = fields.Many2one('res.branch', string='Branch', required=True, index=True, domain="[('company_id','=',company_id)]")
    state = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('submitted', 'Submitted'), ('verified', 'Verified'), ('paid', 'Paid'), ('canceled', 'Cancelled')], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    amount = fields.Monetary(string="Total", currency_field='currency_id', compute='_compute_amount')
    receipt_voucher_line_ids = fields.One2many('receipt.voucher.line', 'receipt_voucher_id', string="Receipt Voucher Line")
    invoice_cutoff_date = fields.Date(string='Cut Off Date', tracking=True)
    customer_allowed_ids = fields.Many2many('account.move', compute="_compute_customer_allowed_ids")
    is_cutoff_date = fields.Boolean(string='Is Cut Off Date', compute='_get_cut_off_date_config')

    def check_closed_period(self):
        check_periods = self.env['sh.account.period'].search([('company_id', '=', self.company_id.id), ('branch_id', '=', self.branch_id.id), ('state', '=', 'done'),('date_start', '<=', self.voucher_date), ('date_end', '>=', self.voucher_date)])
        if check_periods:
            raise UserError(_('You can not post any journal entry already on Closed Period'))
    
    # def create(self, vals):
    #     result = super(ReceiptVoucher, self).create(vals)
    #     check_periods = self.env['sh.account.period'].search([('company_id', '=', self.company_id.id), ('branch_id', '=', self.branch_id.id), ('state', '=', 'done'),('date_start', '<=', self.voucher_date), ('date_end', '>=', self.voucher_date)])
    #     if check_periods:
    #         raise UserError(_('You can not post any journal entry already on Closed Period'))
    #     return result

    # def write(self, vals):
    #     result = super(ReceiptVoucher, self).write(vals)
    #     check_periods = self.env['sh.account.period'].search([('company_id', '=', self.company_id.id), ('branch_id', '=', self.branch_id.id), ('state', '=', 'done'),('date_start', '<=', self.voucher_date), ('date_end', '>=', self.voucher_date)])
    #     if check_periods:
    #         raise UserError(_('You can not post any journal entry already on Closed Period'))
    #     return result
    
    def unlink(self):
        for rec in self:
            if rec.state not in ['draft','canceled']:
                raise UserError(_('You can not delete a receipt voucher which is not in draft or canceled state.'))
        return super(ReceiptVoucher, self).unlink()

    def _valid_field_parameter(self, field, name):
        return name == "track_visibility" or super()._valid_field_parameter(field, name)
        
    @api.onchange('voucher_date')
    @api.depends('voucher_date')
    def set_cutoff_date(self):
        is_cutoff_date = self.env['ir.config_parameter'].sudo().get_param('is_invoice_cutoff_date', False)
        if is_cutoff_date:
            cutoff_date = self.env['ir.config_parameter'].sudo().get_param('invoice_cutoff_date', '1')
            for rec in self:
                if rec.voucher_date:
                    if int(cutoff_date) <= int(self.last_day_of_month(rec.voucher_date).day):
                        if rec.voucher_date.day < int(cutoff_date):
                            rec.invoice_cutoff_date = datetime(rec.voucher_date.year, rec.voucher_date.month, int(cutoff_date)) - relativedelta(months=1)
                        else:
                            rec.invoice_cutoff_date = datetime(rec.voucher_date.year, rec.voucher_date.month, int(cutoff_date))
                    else:
                        if rec.voucher_date.day < int(cutoff_date):
                            rec.invoice_cutoff_date = datetime(rec.voucher_date.year, rec.voucher_date.month, int(self.last_day_of_month(rec.voucher_date).day)) - relativedelta(months=1)
                        else:
                            rec.invoice_cutoff_date = datetime(rec.voucher_date.year, rec.voucher_date.month, int(self.last_day_of_month(rec.voucher_date).day))

    def last_day_of_month(self, day):
        next_month = day.replace(day=28) + relativedelta(days=4)
        return next_month - relativedelta(days=next_month.day) 

    def _get_cut_off_date_config(self):
        for record in self:
            is_cutoff_date = self.env['ir.config_parameter'].sudo().get_param('is_invoice_cutoff_date', False)
            record.is_cutoff_date = is_cutoff_date

    @api.depends('partner_ids', 'voucher_date', 'invoice_cutoff_date')
    def _compute_customer_allowed_ids(self):
        am = self.env['account.move']
        is_cutoff_date = self.env['ir.config_parameter'].sudo().get_param('is_invoice_cutoff_date', False)
        for m in self:
            if is_cutoff_date:
                domain = [('partner_id','in',m.partner_ids.ids), ('move_type','=','out_invoice'), ('state','=','posted'), ('invoice_date','<',m.invoice_cutoff_date), ('payment_state', 'in', ['not_paid', 'partial'])]
            else:
                domain = [('partner_id','in',m.partner_ids.ids), ('move_type','=','out_invoice'), ('state','=','posted'), ('payment_state', 'in', ['not_paid', 'partial'])]
            m.customer_allowed_ids = am.search(domain)

    def action_submit(self):
        self.check_closed_period()
        for res in self:
            res.state = 'submitted'
        return True
    
    def action_verify(self):
        for res in self:
            res.state = 'verified'
        return True
    
    def action_cancel(self):
        for res in self:
            res.state = 'cancel'
        return True
    
    def action_pay(self):
        for line in self.receipt_voucher_line_ids:
            to_reconcile = []
            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': line.invoice_id.partner_id.id,
                'amount': line.amount,
                'payment_date': self.voucher_date,
                'journal_id': self.bank_id.id,
                'payment_reference': self.name,
                'currency_id': self.currency_id.id,
                'branch_id': self.branch_id.id,
                'destination_account_id': line.invoice_id.partner_id.property_account_receivable_id.id,
                'receipt_voucher_id': self.id,
                'invoice_origin_id': line.invoice_id.id,
            }
            if line.invoice_id.partner_id and line.invoice_id.partner_id.bank_ids:
                payment_vals['partner_bank_id'] = line.invoice_id.partner_id.bank_ids[0].id
            elif self.bank_id.inbound_payment_method_ids:
                payment_vals['payment_method_id'] = self.bank_id.inbound_payment_method_ids[0].id

            payment_id  = self.env['account.payment'].create(payment_vals)
            for line in line.invoice_id.line_ids.filtered_domain([('account_id.internal_type', '=', 'receivable'), ('reconciled', '=', False)]):
                to_reconcile.append(line)

            for payment, lines in zip(payment_id, to_reconcile):
                if payment.currency_id != lines.currency_id:
                    liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
                    source_balance = abs(sum(lines.mapped('amount_residual')))
                    payment_rate = liquidity_lines[0].amount_currency / \
                        liquidity_lines[0].balance
                    source_balance_converted = abs(
                        source_balance) * payment_rate

                    # Translate the balance into the payment currency is order to be able to compare them.
                    # In case in both have the same value (12.15 * 0.01 ~= 0.12 in our example), it means the user
                    # attempt to fully paid the source lines and then, we need to manually fix them to get a perfect
                    # match.
                    payment_balance = abs(
                        sum(counterpart_lines.mapped('balance')))
                    payment_amount_currency = abs(
                        sum(counterpart_lines.mapped('amount_currency')))
                    if not payment.currency_id.is_zero(source_balance_converted - payment_amount_currency):
                        continue

                    delta_balance = source_balance - payment_balance

                    # Balance are already the same.
                    if self.company_id.currency_id.is_zero(delta_balance):
                        continue

                    # Fix the balance but make sure to peek the liquidity and counterpart lines first.
                    debit_lines = (liquidity_lines +
                                   counterpart_lines).filtered('debit')
                    credit_lines = (liquidity_lines +
                                    counterpart_lines).filtered('credit')

                    payment.move_id.write({'line_ids': [
                        (1, debit_lines[0].id, {
                         'debit': debit_lines[0].debit + delta_balance}),
                        (1, credit_lines[0].id, {
                         'credit': credit_lines[0].credit + delta_balance}),
                    ]})
            payment_id.action_post()
            domain = [('account_internal_type', 'in', ('receivable',
                                                       'payable')),
                      ('reconciled', '=', False)]
            for payment, lines in zip(payment_id, to_reconcile):
                if payment.state != 'posted':
                    continue
                payment_lines = payment.line_ids.filtered_domain(domain)
                for account in payment_lines.account_id:
                    (payment_lines + lines)\
                        .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                        .reconcile()
        self.state = 'paid'
        self.receipt_voucher_line_ids._onchange_invoice_id()

    
    def set_to_draft(self):
        for res in self:
            res.state = 'draft'
        return True
    
    @api.onchange('customer_invoice_ids')
    def _onchange_customer_invoice_ids(self):
        self.receipt_voucher_line_ids = False
        for invoice in self.customer_invoice_ids:
            if not self.receipt_voucher_line_ids.filtered(lambda x: x.invoice_id.id == invoice._origin.id):
                receipt_line_id = self.env['receipt.voucher.line'].create({
                    'receipt_voucher_id': self._origin.id,
                    'invoice_id': invoice._origin.id,
                })
                receipt_line_id._onchange_invoice_id()
                self.receipt_voucher_line_ids = [(4, receipt_line_id.id)]
        for line in self.receipt_voucher_line_ids:
            if not self.customer_invoice_ids.filtered(lambda x: x._origin.id == line.invoice_id.id):
                self.receipt_voucher_line_ids = [(2, line.id)]
        self.amount = sum(self.receipt_voucher_line_ids.mapped('amount'))
        
    @api.depends('receipt_voucher_line_ids')
    def _compute_amount(self):
        for rec in self:
            amount = 0.0
            for line in rec.receipt_voucher_line_ids:
                amount += line.total_invoice_amount
            rec.amount = amount
            if rec.receipt_voucher_line_ids:
                rec.receipt_voucher_line_ids._onchange_invoice_id()


    def _get_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    def action_view_payment(self):
        action = self.env.ref('account.action_account_payments').read()[0]
        action['domain'] = [('id', 'in', self.payment_ids.ids)]
        return action


    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence']. next_by_code('receipt.voucher.code') or _('New')
        result = super(ReceiptVoucher, self).create(vals)
        return result

class ReceiptVoucherLine(models.Model):
    _name = "receipt.voucher.line"
    _description = "Receipt Voucher Line"
    

    receipt_voucher_id = fields.Many2one('receipt.voucher', string="Receipt Voucher")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    invoice_date = fields.Date(string="Invoice Date")
    untaxed_amount = fields.Monetary(string="Untaxed Amount", currency_field='currency_id')
    tax_amount = fields.Monetary(string="Tax Amount", currency_field='currency_id')
    total_invoice_amount = fields.Monetary(string="Total Invoice Amount", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string="Currency")
    amount_due = fields.Monetary(string="Amount Due", currency_field='currency_id')
    amount = fields.Monetary(string="Allocation Amount", currency_field='currency_id')
    total_amount = fields.Monetary(string="Total Amount", currency_field='currency_id')
    company_id = fields.Many2one(related='receipt_voucher_id.company_id', string='Company', store=True, readonly=True, index=True)
    partner_id = fields.Many2one('res.partner')
    

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        for receipt in self:
            if receipt.invoice_id:
                receipt.invoice_date = receipt.invoice_id.invoice_date
                receipt.untaxed_amount = receipt.invoice_id.amount_untaxed
                receipt.tax_amount = receipt.invoice_id.amount_tax
                receipt.total_invoice_amount = receipt.invoice_id.amount_total
                receipt.currency_id = receipt.invoice_id.currency_id.id
                receipt.amount_due = receipt.invoice_id.amount_residual
                receipt.amount = receipt.invoice_id.amount_residual
                receipt.total_amount = receipt.invoice_id.amount_residual
                receipt.partner_id = receipt.invoice_id.partner_id
    

