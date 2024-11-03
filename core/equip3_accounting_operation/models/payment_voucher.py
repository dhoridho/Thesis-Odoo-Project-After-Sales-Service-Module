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


class PaymentVoucher(models.Model):
    _name = 'payment.voucher'
    _description = 'Payment Voucher'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "name desc"

    def _default_currency_id(self):
        company_id = self.env.context.get('force_company') or self.env.context.get(
            'company_id') or self.env.company.id
        return self.env['res.company'].browse(company_id).currency_id

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
    def _domain_partner_ids(self):
        return [('is_vendor','=',True)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)
    create_by = fields.Many2one('res.users','Created By',default=lambda self: self.env.user)
    name = fields.Char('Payment Voucher', required=True, default='/')
    partner_id = fields.Many2one('res.partner', 'Payee Name')
    partner_ids = fields.Many2many('res.partner', 'payment_voucher_rel', 'payment_voucher_rec', 'partner_id', string='Payee Names', required=True, domain=_domain_partner_ids)
    date = fields.Date('Date', default=fields.Date.today())
    bank_id = fields.Many2one('account.journal', domain="[('type','in',['bank','cash'])]", string='Bank', required=True)
    cheque_number = fields.Char('Cheque Number')
    cheque_date = fields.Date('Cheque Date')
    vendor_bill_ids = fields.Many2many('account.move', relation='payment_vendor_bills_rel', string='Vendor Bills', domain="[('id', 'in', vendor_allowed_ids), ('payment_state', '!=', 'paid'), ('move_type','=','in_invoice'), ('state', '=', 'posted')]", required=True)
    # vendor_bill_ids = fields.Many2many('account.move', relation='payment_vendor_bills_rel', string='Vendor Bills', required=True, domain="[('id', 'in', vendor_allowed_ids)]")
    remarks = fields.Text('Remarks')
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    request_partner_id = fields.Many2one('res.partner', string="Requested Partner")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=_default_currency_id)
    line_ids = fields.One2many('payment.voucher.line', 'voucher_id', 'Invoice Information')
    
    state = fields.Selection([('draft', 'Draft'),
                              ('to_approve', 'Waiting For Approval'),
                              ('approved', 'Approved'),
                              ('rejected', 'Rejected'),
                              ('submitted', 'Submitted'),
                              ('verified', 'Verified'), ('paid', 'Paid'),
                              ('canceled', 'Canceled')],
                             track_visibility='onchange',
                             default="draft")
    amount = fields.Monetary('Total', currency_field='currency_id', compute='_compute_voucher_total')
    amount_text = fields.Char('Amount in Words')
    payment_ids = fields.One2many('account.payment', 'voucher_id', 'Payments')
    payment_count = fields.Integer(compute='_get_payment_count')
    approval_matrix_id = fields.Many2one('approval.matrix.accounting', string="Approval Matrix", compute='_get_approval_matrix')
    is_payment_voucher_approval_matrix = fields.Boolean(string="Is Payment Voucher Approval Matrix", compute='_get_approve_button_from_config')
    approved_matrix_ids = fields.One2many('approval.matrix.accounting.lines', 'payment_voc_id', string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.accounting.lines', string='Approval Matrix Line', compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    state1 = fields.Selection(related="state", tracking=False)
    state2 = fields.Selection(related="state", tracking=False)
    amount_to_text = fields.Char(compute='_amount_in_words', string='In Words', help="The amount in words")
    amount_to_text = fields.Char(compute='_amount_in_words', string='In Words', help="The amount in words")
    invoice_cutoff_date = fields.Date(string='Cut Off Date', tracking=True)
    vendor_allowed_ids = fields.Many2many('account.move', compute="_compute_vendor_allowed_ids")
    is_cutoff_date = fields.Boolean(string='Is Cut Off Date', compute='_get_cut_off_date_config')


    def unlink(self):
        for rec in self:
            if rec.state not in ['draft', 'canceled']:
                raise ValidationError(
                    _('You can not delete a record which is not in draft or canceled state.'))
        return super(PaymentVoucher, self).unlink()

    def _valid_field_parameter(self, field, name):
        return name == "track_visibility" or super()._valid_field_parameter(field, name)

    @api.onchange('date')
    @api.depends('date')
    def set_cutoff_date(self):
        is_cutoff_date = self.env['ir.config_parameter'].sudo().get_param('is_invoice_cutoff_date', False)
        if is_cutoff_date:
            cutoff_date = self.env['ir.config_parameter'].sudo().get_param('invoice_cutoff_date', '1')
            for rec in self:
                if rec.date:
                    if int(cutoff_date) <= int(self.last_day_of_month(rec.date).day):
                        if rec.date.day < int(cutoff_date):
                            rec.invoice_cutoff_date = datetime(rec.date.year, rec.date.month, int(cutoff_date)) - relativedelta(months=1)
                        else:
                            rec.invoice_cutoff_date = datetime(rec.date.year, rec.date.month, int(cutoff_date))
                    else:
                        if rec.date.day < int(cutoff_date):
                            rec.invoice_cutoff_date = datetime(rec.date.year, rec.date.month, int(self.last_day_of_month(rec.date).day)) - relativedelta(months=1)
                        else:
                            rec.invoice_cutoff_date = datetime(rec.date.year, rec.date.month, int(self.last_day_of_month(rec.date).day))

    def last_day_of_month(self, day):
        next_month = day.replace(day=28) + relativedelta(days=4)
        return next_month - relativedelta(days=next_month.day) \

    def _get_cut_off_date_config(self):
        for record in self:
            is_cutoff_date = self.env['ir.config_parameter'].sudo().get_param('is_invoice_cutoff_date', False)
            record.is_cutoff_date = is_cutoff_date

    @api.depends('partner_ids','date', 'invoice_cutoff_date')
    def _compute_vendor_allowed_ids(self):
        am = self.env['account.move']
        is_cutoff_date = self.env['ir.config_parameter'].sudo().get_param('is_invoice_cutoff_date', False)
        for m in self:
            if is_cutoff_date:
                domain = [('partner_id','in',m.partner_ids.ids),('move_type','=','in_invoice'), ('state','=','posted'), ('invoice_date','<',m.invoice_cutoff_date), ('payment_state', 'in', ['not_paid', 'partial'])]
            else:
                domain = [('partner_id','in',m.partner_ids.ids),('move_type','=','in_invoice'), ('state','=','posted'), ('payment_state', 'in', ['not_paid', 'partial'])]
            m.vendor_allowed_ids = am.search(domain)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        for res in self:
            domain.extend([('company_id', '=', res.env.company.id)])
        return super(PaymentVoucher, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        for res in self:
            domain.extend([('company_id', '=', res.env.company.id)])
        return super(PaymentVoucher, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit,
                                                      orderby=orderby, lazy=lazy)


    @api.depends('amount', 'line_ids.invoice_number_id.partner_id', 'line_ids.invoice_number_id.partner_id.lang')
    def _amount_in_words(self):
        # amounttotext = self.env['account.move']
        for obj in self:
            if obj.line_ids.invoice_number_id.partner_id[0].lang == 'nl_NL':
                obj.amount_to_tex
                t = amount_to_text.amount_to_text_nl(
                    obj.amount, currency='euro')
            else:
                try:
                    obj.amount_to_text = num2words(
                        obj.amount, lang=obj.line_ids.invoice_number_id.partner_id[0].lang).title()
                except NotImplementedError:
                    obj.amount_to_text = num2words(
                        obj.amount, lang='en').title()

    @api.depends('line_ids', 'line_ids.amount', 'company_id', 'branch_id')
    def _get_approval_matrix(self):
        for record in self:
            amount = sum(record.line_ids.mapped('amount'))
            matrix_id = self.env['approval.matrix.accounting'].search([
                ('company_id', '=', record.company_id.id),
                ('branch_id', '=', record.branch_id.id),
                ('min_amount', '<=', amount),
                ('max_amount', '>=', amount),
                ('approval_matrix_type', '=', 'payment_voucher')
            ], limit=1)
            record.approval_matrix_id = matrix_id
            record._compute_approving_matrix_lines()

    def _get_approve_button_from_config(self):
        for record in self:
            is_payment_voucher_approval_matrix = self.env['ir.config_parameter'].sudo(
            ).get_param('is_payment_voucher_approval_matrix', False)
            record.is_payment_voucher_approval_matrix = is_payment_voucher_approval_matrix

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(
                lambda r: not r.approved), key=lambda r: r.sequence)
            if len(matrix_line) == 0:
                record.is_approve_button = False
                record.approval_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button = True
                    record.approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button = False
                    record.approval_matrix_line_id = False
            else:
                record.is_approve_button = False
                record.approval_matrix_line_id = False

    @api.onchange('approval_matrix_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.state == 'draft' and record.is_payment_voucher_approval_matrix:
                record.approved_matrix_ids = []
                counter = 1
                record.approved_matrix_ids = []
                for rec in record.approval_matrix_id:
                    for line in rec.approval_matrix_line_ids:
                        data.append((0, 0, {
                            'sequence': counter,
                            'user_ids': [(6, 0, line.user_ids.ids)],
                            'minimum_approver': line.minimum_approver,
                        }))
                        counter += 1
                record.approved_matrix_ids = data

    def action_request_for_approval(self):
        self.check_closed_period()
        for record in self:
            action_id = self.env.ref('equip3_accounting_operation.vendor_voucher_payment_action')
            template_id = self.env.ref('equip3_accounting_operation.email_template_payment_voucher_approval_matrix')
            wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_request_for_payment_voucher')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + \
                str(record.id) + '&action=' + str(action_id.id) + \
                '&view_type=form&model=payment.voucher'
            currency = record.currency_id.symbol + str(record.amount)
            record.request_partner_id = self.env.user.partner_id.id
            invoice_name = 'Draft Payment Voucher' if record.state != 'posted' else record.name
            for partner in record.partner_ids:
                if record.approved_matrix_ids and len(record.approved_matrix_ids[0].user_ids) > 1:
                    for approved_matrix_id in record.approved_matrix_ids[0].user_ids:
                        approver = approved_matrix_id
                        ctx = {
                            'email_from': self.env.user.company_id.email,
                            'email_to': approver.partner_id.email,
                            'approver_name': approver.name,
                            'date': date.today(),
                            'submitter': self.env.user.name,
                            'url': url,
                            'invoice_name': invoice_name,
                            "currency": currency,
                            "payee_name": partner.name,
                            "bank" : record.bank_id.name,
                        }
                        template_id.with_context(ctx).send_mail(record.id, True)
                        record._send_whatsapp_message(wa_template_id, approver, currency, url)
                else:
                    approver = record.approved_matrix_ids[0].user_ids[0]
                    ctx = {
                        'email_from': self.env.user.company_id.email,
                        'email_to': approver.partner_id.email,
                        'approver_name': approver.name,
                        'date': date.today(),
                        'submitter': self.env.user.name,
                        'url': url,
                        'invoice_name': invoice_name,
                        "currency": currency,
                        "payee_name": partner.name,
                        "bank" : record.bank_id.name,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    record._send_whatsapp_message(wa_template_id, approver, currency, url)

                record.write({'state': 'to_approve'})

    def action_approve(self):
        for record in self:
            
            action_id = self.env.ref('equip3_accounting_operation.vendor_voucher_payment_action')
            template_id_submitter = self.env.ref('equip3_accounting_operation.email_template_payment_voucher_submitter_approval_matrix')
            wa_template_submitted = self.env.ref('equip3_accounting_operation.wa_template_approval_payment_voucher')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + \
                str(record.id) + '&action=' + str(action_id.id) + \
                '&view_type=form&model=payment.voucher'
            currency = record.currency_id.symbol + str(record.amount)
            record.request_partner_id = self.env.user.partner_id.id
            invoice_name = 'Draft Payment Voucher' if record.state != 'posted' else record.name
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                        user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(
                        local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (
                            self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (
                            self.env.user.name, local_datetime)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write(
                            {'time_stamp': datetime.now(), 'approved': True})
                        # next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        # if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].approver) > 1:
                        #     pass
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                record.write({'state': 'approved'})
                record.verify()
                email_to = record.request_partner_id.email 
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': email_to,
                    'approver_name': record.name,
                    'date': date.today(),
                    'create_date': record.create_date.date(),
                    'submitter': self.env.user.name,
                    'url': url,
                    'invoice_name': invoice_name,
                    "date_invoice": record.date,
                    "currency": currency,
                }
                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                record._send_whatsapp_message(
                    wa_template_submitted, record.request_partner_id.user_ids, currency, url)
                
    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment Voucher Marix Reject ',
            'res_model': 'payment.voucher.matrix.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.model
    def _send_whatsapp_message(self, template_id, approver, currency=False, url=False, reason=False):
        wa_sender = waParam()
        # template = self.env.ref('equip3_accounting_operation.wa_template_application_for_invoice_approval')
        for record in self:
            string_test = str(template_id.message)
            
            if "${approver_name}" in string_test:
                string_test = string_test.replace(
                    "${approver_name}", approver.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace(
                    "${submitter_name}", record.request_partner_id.name)
            if "${amount_invoice}" in string_test:
                string_test = string_test.replace(
                    "${amount_invoice}", str(record.amount_total))
            if "${currency}" in string_test:
                string_test = string_test.replace("${currency}", currency)
            if "${partner_name}" in string_test:
                string_test = string_test.replace(
                    "${partner_name}", record.partner_id.name)
            if "${due_date}" in string_test:
                string_test = string_test.replace("${due_date}", fields.Datetime.from_string(
                    record.invoice_date_due).strftime('%d/%m/%Y'))
            if "${date_invoice}" in string_test:
                string_test = string_test.replace("${date_invoice}", fields.Datetime.from_string(
                    record.invoice_date).strftime('%d/%m/%Y'))
            if "${create_date}" in string_test:
                string_test = string_test.replace("${create_date}", fields.Datetime.from_string(
                    record.create_date).strftime('%d/%m/%Y'))
            if "${feedback}" in string_test:
                string_test = string_test.replace("${feedback}", reason)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            if "${bank}" in string_test:
                string_test = string_test.replace("${bank}", record.bank_id.name)
            for partner in record.partner_ids:
                if "${payee_name}" in string_test:
                    string_test = string_test.replace("${payee_name}", partner.name)
            phone_num = str(approver.mobile or approver.employee_phone)
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "")
            wa_sender.set_wa_string(string_test, template_id._name, template_id=template_id)
            wa_sender.send_wa(phone_num)


    @api.depends('line_ids')
    def _compute_voucher_total(self):
        for payment in self:
            total = 0
            for line in payment.line_ids:
                total += line.amount
            payment.amount = total
            if payment.line_ids:
                payment.line_ids._onchange_invoice_number()

    @api.onchange('partner_id', 'date')
    def branch_domain(self):
        res = {}
        self._get_approve_button_from_config()
        if self.create_by and self.create_by.branch_ids:
            res = {
                'domain': {
                    'branch_id': [('id', 'in', self.env.branches.ids),('company_id','=', self.env.company.id)]
                }
            }
        return res

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        return

    @api.onchange('vendor_bill_ids')
    def _onchange_vendor_bill_ids(self):
        for bill in self.vendor_bill_ids:
            if not self.line_ids.filtered(
                    lambda x: x.invoice_number_id.id == bill._origin.id):
                voucher_line_id = self.env['payment.voucher.line'].create({
                    'invoice_number_id':
                    bill._origin.id,
                    'voucher_id':
                    self._origin.id
                })
                voucher_line_id._onchange_invoice_number()
                self.line_ids = [(4, voucher_line_id.id)]
        for line in self.line_ids:
            if not self.vendor_bill_ids.filtered(
                    lambda x: x._origin.id == line.invoice_number_id.id):
                self.line_ids = [(2, line.id)]

    def set_to_draft(self):
        self.state = 'draft'

    def check_closed_period(self):
        check_periods = self.env['sh.account.period'].search([('company_id', '=', self.company_id.id),('branch_id', '=', self.branch_id.id), ('state', '=', 'done'), ('date_start', '<=', self.date), ('date_end', '>=', self.date)])
        if check_periods:
            raise UserError(_('You can not post any journal entry already on Closed Period'))
        
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('payment.voucher.code') or _('New')
        return super(PaymentVoucher, self).create(vals)

    def submit(self):
        self.check_closed_period()
        self.write({'state': 'submitted'})
        # self.write({
        #     'name': self.env['ir.sequence']. next_by_code('payment.voucher.code') or _('New'),
        #     'state': 'submitted'
        # })

    def verify(self):
        self.state = 'verified'

    def pay(self):
        for line in self.line_ids:
            to_reconcile = []
            payment_values = {
                'company_id': self.company_id.id,
                'partner_id': line.invoice_number_id.partner_id.id,
                'amount': line.amount,
                'date': self.date,
                'ref': self.cheque_number,
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'currency_id': self.currency_id.id,
                'branch_id': self.branch_id.id,
                # 'destination_account_id': line.invoice_number_id.line_ids[0].account_id.id,
                'destination_account_id': line.invoice_number_id.partner_id.property_account_payable_id.id,
                'journal_id': self.bank_id.id,
                'voucher_id': self.id,
                'invoice_origin_id': line.invoice_number_id.id,
            }
            if line.invoice_number_id.partner_id and line.invoice_number_id.partner_id.bank_ids:
                payment_values['partner_bank_id'] = line.invoice_number_id.partner_id.bank_ids[0].id
            elif self.bank_id.outbound_payment_method_ids:
                payment_values['payment_method_id'] = self.bank_id.outbound_payment_method_ids[0].id

            payment_id = self.env['account.payment'].create(payment_values)
            for line in line.invoice_number_id.line_ids.filtered_domain([('account_internal_type', 'in', ('receivable','payable')),('reconciled', '=', False)]):
                to_reconcile.append(line)

            for payment, lines in zip(payment_id, to_reconcile):
                # Batches are made using the same currency so making 'lines.currency_id' is ok.
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
        self.line_ids._onchange_invoice_number()

    def cancel(self):
        for res in self:
            res.state = 'canceled'

    def _get_payment_count(self):
        for res in self:
            res.payment_count = len(res.payment_ids)

    def get_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'view_mode': 'tree',
            'res_model': 'account.payment',
            'domain': [('id', 'in', self.payment_ids.ids)],
            'context': "{'create': False}",
            'view_id': self.env.ref('account.view_account_supplier_payment_tree').id,
        }

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False


class PaymentVoucherLine(models.Model):
    _name = 'payment.voucher.line'
    _description = 'Payment voucher Line'

    invoice_number_id = fields.Many2one('account.move', 'Invoice Number')
    invoice_date = fields.Date('Date', related='invoice_number_id.date')
    currency_id = fields.Many2one('res.currency',
                                  readonly=True,
                                  related='invoice_number_id.currency_id')
    untaxed_amount = fields.Monetary(
        'Untaxed Amount',
        # related='invoice_number_id.amount_untaxed',
        store=True)
    tax_amount = fields.Monetary(
        'Tax Amount',
        # related='invoice_number_id.amount_tax',
        store=True)
    total_invoice_amount = fields.Monetary(
        'Total'
        # related='invoice_number_id.amount_total'
    )
    amount_due = fields.Monetary(
        'Amount Due',
        # related='invoice_number_id.amount_residual',
        store=True)
    amount = fields.Monetary('Amount')
    voucher_id = fields.Many2one('payment.voucher', 'Payment Voucher')
    state = fields.Selection([('processing', 'Processing'), ('paid', 'Paid')],
                             default='processing',
                             compute='_get_voucherline_state',
                             store=True)

    voucher_state = fields.Selection(related='voucher_id.state')
    partner_id = fields.Many2one('res.partner', related='invoice_number_id.partner_id')

    @api.depends('amount_due')
    def _get_voucherline_state(self):
        for voucher in self:
            if voucher.amount_due <= 0:
                voucher.state = 'paid'
            else:
                voucher.state = 'processing'

    @api.onchange('invoice_number_id')
    def _onchange_invoice_number(self):
        for voucher in self:
            if voucher.invoice_number_id:
                voucher.untaxed_amount = voucher.invoice_number_id.amount_untaxed
                voucher.tax_amount = voucher.invoice_number_id.amount_tax
                voucher.total_invoice_amount = voucher.invoice_number_id.amount_total
                voucher.amount_due = voucher.invoice_number_id.amount_residual
                voucher.amount = voucher.invoice_number_id.amount_residual

    @api.onchange('amount')
    def onchange_amount(self):
        for rec in self:
            if rec.amount > rec.amount_due:
                raise ValidationError('The payment can not exceed the amount due. Please check the amount you want to pay!')

class ApprovalMatrixAccountingLines(models.Model):
    _inherit = "approval.matrix.accounting.lines"

    payment_voc_id = fields.Many2one(
        'payment.voucher', string='Payment Voucher')
