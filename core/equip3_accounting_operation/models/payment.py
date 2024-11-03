# -*- coding: utf-8 -*-
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from lxml import etree
from odoo.addons.base.models.ir_ui_view import (transfer_field_to_modifiers, transfer_node_to_modifiers, transfer_modifiers_to_node)
from datetime import datetime, date, timedelta
from num2words import num2words
import logging
import requests
import json
import base64
from ast import literal_eval
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

_logger = logging.getLogger(__name__)

def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers)
    transfer_node_to_modifiers(
        node, modifiers, context=context)
    transfer_modifiers_to_node(modifiers, node)


class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountPayment, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        context = self._context
        doc = etree.XML(res['arch'])
        
        if context.get('default_payment_type') != 'outbound' or  context.get('default_partner_type') != 'supplier':
            if doc.xpath("//field[@name='administration']"):
                node = doc.xpath("//field[@name='administration']")[0]
                node.set('invisible', '1')
                setup_modifiers(node, res['fields']['administration'])
        res['arch'] = etree.tostring(doc, encoding='unicode')
        
        return res

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id




    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        domain=_domain_branch,
        default = _default_branch,
        readonly=False)
    
    user_id = fields.Many2one('res.users','User',default=lambda self:self.env.user)
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry', required=True,
        readonly=True, ondelete='cascade',
        tracking=True,
        check_company=True)

    is_reconciled = fields.Boolean(
        string="Is Reconciled", store=True,
        tracking=True,
        compute='_compute_reconciliation_status',
        help="Technical field indicating if the payment is already reconciled.")
    is_matched = fields.Boolean(
        string="Is Matched With a Bank Statement", store=True,
        tracking=True,
        compute='_compute_reconciliation_status',
        help="Technical field indicating if the payment has been matched with a statement line.")
    partner_bank_id = fields.Many2one(
        'res.partner.bank', string="Recipient Bank Account",
        tracking=True,
        readonly=False, store=True,
        compute='_compute_partner_bank_id',
        domain="[('partner_id', '=', partner_id)]",
        check_company=True)
    is_internal_transfer = fields.Boolean(
        string="Is Internal Transfer",
        tracking=True,
        readonly=False, store=True,
        compute="_compute_is_internal_transfer")
    qr_code = fields.Char(
        string="QR Code",
        compute="_compute_qr_code",
        help="QR-code report URL to use to generate the QR-code to scan with a banking app to perform this payment.")

    # == Payment methods fields ==
    payment_method_id = fields.Many2one(
        'account.payment.method', string='Payment Method',
        tracking=True,
        readonly=False, store=True,
        compute='_compute_payment_method_id',
        domain="[('id', 'in', available_payment_method_ids)]",
        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n"\
        "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n"\
        "Check: Pay bill by check and print it from Odoo.\n"\
        "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n"\
        "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")
    available_payment_method_ids = fields.Many2many(
        'account.payment.method',
        compute='_compute_payment_method_fields')
    hide_payment_method = fields.Boolean(
        compute='_compute_payment_method_fields',
        help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")

    # == Synchronized fields with the account.move.lines ==
    amount = fields.Monetary(
        currency_field='currency_id',
        tracking=True)
    payment_type = fields.Selection(
        [
            ('outbound', 'Send Money'),
            ('inbound', 'Receive Money'),
        ], tracking=True,
        string='Payment Type', default='inbound', required=True)
    payment_reference = fields.Char(
        string="Payment Reference", copy=False,
        tracking=True,
        help="Reference of the document used to issue this payment. Eg. check number, file name, etc.")
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        tracking=True, store=True, readonly=False,
        compute='_compute_currency_id',
        help="The payment's currency.")
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer/Vendor",
        store=True, readonly=False, ondelete='restrict',
        compute='_compute_partner_id',
        domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
        tracking=True,
        check_company=True)
    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        compute='_compute_destination_account_id',
        domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
        tracking=True,
        check_company=True)

    # == Stat buttons ==
    reconciled_invoice_ids = fields.Many2many(
        'account.move', string="Reconciled Invoices",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Invoices whose journal items have been reconciled with these payments.")
    reconciled_invoices_count = fields.Integer(
        string="# Reconciled Invoices",
        compute="_compute_stat_buttons_from_reconciliation")
    reconciled_bill_ids = fields.Many2many(
        'account.move', string="Reconciled Bills",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Invoices whose journal items have been reconciled with these payments.")
    reconciled_bills_count = fields.Integer(
        string="# Reconciled Bills",
        compute="_compute_stat_buttons_from_reconciliation")
    reconciled_statement_ids = fields.Many2many(
        'account.move', string="Reconciled Statements",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Statements matched to this payment")
    reconciled_statements_count = fields.Integer(
        string="# Reconciled Statements",
        compute="_compute_stat_buttons_from_reconciliation")

    # == Display purpose fields ==
    payment_method_code = fields.Char(
        related='payment_method_id.code',
        tracking=True,
        help="Technical field used to adapt the interface to the payment type selected.")
    show_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank',
        help="Technical field used to know whether the field `partner_bank_id` needs to be displayed or not in the payments form views")
    require_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank',
        help="Technical field used to know whether the field `partner_bank_id` needs to be required or not in the payments form views")
    country_code = fields.Char(
        related='company_id.country_id.code', tracking=True)
    voucher_id = fields.Many2one('payment.voucher','Payment Voucher')
    receipt_voucher_id = fields.Many2one('receipt.voucher','Receipt Voucher')
    
    # branch_id = fields.Many2one(
    #     'res.branch',
    #     related='user_id.branch_id',
    #     readonly=False, domain="[('company_id', '=', company_id)]")

    

    payment_receipt_approval_matrix_id = fields.Many2one('approval.matrix.accounting', string="Approval Matrix", compute='_get_payment_receipt_approval_matrix')
    is_receipt_approval_matrix = fields.Boolean(string="Is Receipt Approval Matrix", compute='_get_payment_receipt_approve_button_from_config')
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button_receipt', store=False)
    approved_matrix_ids = fields.One2many('approval.matrix.accounting.lines', 'receipt_id', string="Approved Matrix")
    siganture_history_ids = fields.One2many('payment.signature.history', 'payment_id', string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.accounting.lines', string='Approval Matrix Line', compute='_get_approve_button_receipt', store=False)
    approval_invoice_id = fields.Many2one('account.move', string='Account Move')
    administration = fields.Boolean('Administration')
    analytic_group_ids = fields.Many2many('account.analytic.tag',domain="[('company_id', '=', company_id)]", string="Analytic Group")
    administration_account = fields.Many2one('account.account', string='Administration Account')
    administration_fee = fields.Monetary('Administration Fee', default=0.0, currency_field='company_currency_id')

    manual_currency_exchange_inverse_rate = fields.Float(string='Inverse Rate', digits=(12, 12))
    manual_currency_exchange_rate = fields.Float(string='Manual Currency Exchange Rate', digits=(12, 12), default=0.0)
    # is_from_account_voucher = fields.Boolean(string="Is From Account Voucher", default=False)
    invoice_origin_id  = fields.Many2one('account.move', string='Invoice No.')
    invoice_origin_ids = fields.Many2many('account.move', string='Invoices No.')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        _logger.info(f"Domain: {domain}")
        _logger.info(f"Context: {context}")

        if self.env.context.get('default_partner_type') == 'customer':
            domain += [('partner_type', '=', 'customer')]

        if self.env.context.get('default_partner_type') == 'supplier':
            domain += [('partner_type', '=', 'supplier')]
   
        _logger.info("allowed_company_ids: %s", self.env.context.get('allowed_company_ids'))

        result = super(AccountPayment, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

        return result
    
    @api.depends('move_id.name')
    def name_get(self):
        return [(payment.id, payment.name or _('Draft Payment')) for payment in self]

    @api.onchange('manual_currency_exchange_inverse_rate')
    def _oncange_rate_conversion(self):
        if self.manual_currency_exchange_inverse_rate:
            self.manual_currency_exchange_rate = 1 / self.manual_currency_exchange_inverse_rate
    
    @api.onchange('manual_currency_exchange_rate')
    def _oncange_rate(self):
        if self.manual_currency_exchange_rate:
            self.manual_currency_exchange_inverse_rate = 1 / self.manual_currency_exchange_rate

    @api.onchange('active_manual_currency_rate')
    def _oncange_active_manual(self):
        self.apply_manual_currency_exchange = self.active_manual_currency_rate


    @api.onchange('branch_id')
    def _get_company_id(self):
        self.company_id = self.env.company.id

    @api.onchange('payment_receipt_approval_matrix_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        approver_list = [(5, 0, 0)]
        for record in self:
            if record.state == 'draft' and record.is_receipt_approval_matrix:
                record.approved_matrix_ids = []
                counter = 1
                record.approved_matrix_ids = []
                approver_list = []
                for rec in record.payment_receipt_approval_matrix_id: 
                    for line in rec.approval_matrix_line_ids:
                        data.append((0, 0, {
                            'sequence' : counter,
                            'user_ids' : [(6, 0, line.user_ids.ids)],
                            'minimum_approver' : line.minimum_approver,
                        }))
                        counter += 1
                        for user in line.user_ids:
                            approver_list.append(user.id)
                record.approved_matrix_ids = data
                record.approvers_ids = approver_list

        

    @api.depends('amount', 'company_id', 'branch_id')
    def _get_payment_receipt_approval_matrix(self):
        for record in self:
            matrix_id = False
            context = dict(self.env.context) or {}
            if context.get('default_payment_type') == 'inbound':
                matrix_id = self.env['approval.matrix.accounting'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('min_amount', '<=', record.amount),
                        ('max_amount', '>=', record.amount),
                        ('approval_matrix_type', '=', 'receipt_approval_matrix')
                    ], limit=1)
            elif context.get('default_payment_type') == 'outbound':
                matrix_id = self.env['approval.matrix.accounting'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('min_amount', '<=', record.amount),
                        ('max_amount', '>=', record.amount),
                        ('approval_matrix_type', '=', 'payment_approval_matrix')
                    ], limit=1)
            record.payment_receipt_approval_matrix_id = matrix_id
            record._compute_approving_matrix_lines()

    def _get_payment_receipt_approve_button_from_config(self):
        for record in self:
            is_receipt_approval_matrix = False
            context = dict(self.env.context) or {}
            if context.get('default_payment_type') == 'inbound':
                is_receipt_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_receipt_approval_matrix', False)
            elif context.get('default_payment_type') == 'outbound':
                is_receipt_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_payment_approval_matrix', False)
            record.is_receipt_approval_matrix = is_receipt_approval_matrix

    @api.onchange('partner_id')
    def branch_domain(self):
        res={}
        self._get_payment_receipt_approve_button_from_config()
        if self.user_id and self.user_id.branch_ids:
            res={
            'domain': {
            'branch_id': [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]
            }
        }
        return res

    def _get_approve_button_receipt(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
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
    
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        return
    
    def check_closed_period(self):
        check_periods = self.env['sh.account.period'].search([('company_id', '=', self.company_id.id),('branch_id', '=', self.branch_id.id), ('state', '=', 'done'), ('date_start', '<=', self.date), ('date_end', '>=', self.date)])
        if check_periods:
            raise UserError(_('You can not post any journal entry already on Closed Period'))
    
    def request_for_approval(self):
        check_periods = self.env['sh.account.period'].search([('company_id', '=', self.company_id.id),('branch_id', '=', self.branch_id.id), ('state', '=', 'done'), ('date_start', '<=', self.date), ('date_end', '>=', self.date)])
        if check_periods:
            raise UserError(_('You can not post any journal entry already on Closed Period'))
        for record in self:
            self.check_closed_period()
            if record.payment_type == 'inbound':
                action_id = self.env.ref('account.action_account_payments')
                template_id = self.env.ref(
                    'equip3_accounting_operation.email_template_receipt_approval_matrix')
                wa_template_id = self.env.ref(
                    'equip3_accounting_operation.wa_template_request_for_receipt') 
                invoice_name = 'Draft Receipt' if record.state != 'posted' else record.name       
            elif record.payment_type == 'outbound':
                action_id = self.env.ref('account.action_account_payments_payable')
                template_id = self.env.ref(
                    'equip3_accounting_operation.email_template_payment_approval_matrix')
                wa_template_id = self.env.ref(
                    'equip3_accounting_operation.wa_template_request_for_payment')
                invoice_name = 'Draft Payment' if record.state != 'posted' else record.name
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
            url = base_url + '/web#id=' + \
                str(record.id) + '&action=' + str(action_id.id) + \
                '&view_type=form&model=account.payment'
            currency = record.currency_id.symbol + str(record.amount)
            record.request_partner_id = self.env.user.partner_id.id
            approver = None
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
                        "payment_journal" : record.journal_id.name,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    record._send_whatsapp_message(
                        wa_template_id, approver, currency, url)
            else:
                # approver = record.approved_matrix_ids[0].user_ids[0]
                if record.approved_matrix_ids and record.approved_matrix_ids[0].user_ids:
                    approver = record.approved_matrix_ids[0].user_ids[0]
                    if approver is not None:
                        ctx = {
                            'email_from': self.env.user.company_id.email,
                            'email_to': approver.partner_id.email,
                            'approver_name': approver.name,
                            'date': date.today(),
                            'submitter': self.env.user.name,
                            'url': url,
                            'invoice_name': invoice_name,
                            "currency": currency,
                            "payment_journal" : record.journal_id.name,
                        }
                        template_id.with_context(ctx).send_mail(record.id, True)
                        record._send_whatsapp_message(
                            wa_template_id, approver, currency, url)
                        
                    else:
                        raise UserError(_("No Approver Found"))
   
            record.write({'state': 'to_approve'})

    def action_approved_rp(self):
        for record in self:
            if record.payment_type == 'inbound':
                action_id = self.env.ref('account.action_account_payments')
                template_id_submitter = self.env.ref(
                        'equip3_accounting_operation.email_template_receipt_submitter_approval_matrix')
                wa_template_submitted = self.env.ref(
                        'equip3_accounting_operation.wa_template_approval_receipt')
            elif record.payment_type == 'outbound':
                action_id = self.env.ref('account.action_account_payments_payable')
                template_id_submitter = self.env.ref(
                        'equip3_accounting_operation.email_template_payment_submitter_approval_matrix')
                wa_template_submitted = self.env.ref(
                        'equip3_accounting_operation.wa_template_approval_payment')
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
            url = base_url + '/web#id=' + \
                str(record.id) + '&action=' + str(action_id.id) + \
                '&view_type=form&model=account.voucher'
            currency = record.currency_id.symbol + str(record.amount)
            invoice_name = 'Draft Other Income' if record.state != 'posted' else record.name
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
                        
                    if record.signature_to_confirm:
                        record.siganture_history_ids = [(0,0,{'approver_id':user.id,'signature':user.digital_signature})]

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    record.approved_user_ids = [(4, user.id)]
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write(
                            {'time_stamp': datetime.now(), 'approved': True})
                        next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(
                            lambda r: not r.approved), key=lambda r: r.sequence)
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': approving_matrix_line_user.partner_id.email,
                                    'approver_name': approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter': self.env.user.name,
                                    'url': url,
                                    'invoice_name': invoice_name,
                                    "due_date": record.invoice_date_due,
                                    "date_invoice": record.invoice_date,
                                    "currency": currency,
                                }
                                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                                record._send_whatsapp_message(
                                    wa_template_submitted, approving_matrix_line_user, currency, url)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                # approver = record.approved_matrix_ids[0].user_ids[0]
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                    'approver_name': next_approval_matrix_line_id[0].user_ids[0].name,
                                    'date': date.today(),
                                    'submitter': self.env.user.name,
                                    'url': url,
                                    'invoice_name': invoice_name,
                                    "due_date": record.invoice_date_due,
                                    "date_invoice": record.invoice_date,
                                    "currency": currency,
                                }
                                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                                record._send_whatsapp_message(
                                    wa_template_submitted, next_approval_matrix_line_id[0].user_ids[0], currency, url)
                    # else:
                    #     approval_matrix_line_id.write({'approver_state': 'pending'})
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r:r.approved)):
                record.write({'state': 'approved'})
                record.action_post()
                inv_id = self.env['account.move'].search([('name', '=', record.ref)])
                domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                payment_lines = record.move_id.line_ids.filtered_domain(domain)

                # record.move_id.origin = record.name
                lines = payment_lines
                lines += inv_id.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                lines.reconcile()
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

    def rp_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Approval Marix Reject ',
            'res_model': 'receipt.payment.matrix.reject',
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
                    "${submitter_name}", record.create_uid.partner_id.name)
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
            phone_num = str(approver.mobile or approver.employee_phone)
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "")
            wa_sender.set_wa_string(string_test, template_id._name, template_id=template_id)
            wa_sender.send_wa(phone_num)

        
    
    def _action_reconcile_payment(self, invoice):
        """ Reconcile the payment with the invoice."""
        move_obj = self.env['account.move']
      
        for record in self:
            if record.state == 'posted':
                if record.partner_type == 'customer':
                    if invoice.invoice_id.payment_state == 'not_paid':
                    # if invoice.is_full_reconciled or invoice.amount == invoice.base_amount:
                        to_reconcile = invoice.invoice_id.line_ids.filtered(lambda line: line.account_id.internal_type == 'receivable' and not line.reconciled)
                        domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                        payment_lines = self.payment_id.line_ids.filtered_domain(domain)
                        for account in payment_lines.account_id:
                            lines_to_reconcile = (payment_lines + to_reconcile).filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])
                            if lines_to_reconcile:
                                lines_to_reconcile.reconcile() 

                    elif invoice.invoice_id.payment_state == 'partial':
                        # if invoice.is_full_reconciled or invoice.amount == invoice.base_amount:
                        to_reconcile = invoice.invoice_id.line_ids.filtered(lambda line: line.account_id.internal_type == 'receivable' and not line.reconciled)
                        domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                        payment_lines = self.payment_id.line_ids.filtered_domain(domain)
                        for account in payment_lines.account_id:
                            lines_to_reconcile = (payment_lines + to_reconcile).filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])
                            if lines_to_reconcile:
                                lines_to_reconcile.reconcile() 

                            if lines_to_reconcile[1].amount_residual == 0:
                                invoice.invoice_id.payment_state = 'paid'
                                invoice.invoice_id.amount_residual = 0
                            elif lines_to_reconcile[1].amount_residual < lines_to_reconcile[1].balance:
                                invoice.invoice_id.payment_state = 'partial'
                            else:
                                invoice.invoice_id.payment_state = 'not_paid'
                    
                    # record.write({'is_reconciled' : True})

                elif record.partner_type == 'supplier':
                    to_reconcile = invoice.invoice_id.line_ids.filtered(lambda line: line.account_id.internal_type == 'payable')

                    domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                    payment_lines = self.payment_id.line_ids.filtered_domain(domain)
                    for account in payment_lines.account_id:
                        lines_to_reconcile = (payment_lines + to_reconcile).filtered_domain([('account_id', '=', account.id)])
                        if lines_to_reconcile:
                            lines_to_reconcile.reconcile() 

                        if lines_to_reconcile[1].amount_residual == 0:
                            invoice.invoice_id.payment_state = 'paid'
                            invoice.invoice_id.amount_residual = 0
                        elif lines_to_reconcile[1].amount_residual < invoice.invoice_id.amount_total:
                            invoice.invoice_id.payment_state = 'partial'
                        else:
                            invoice.invoice_id.payment_state = 'not_paid'

                    # record.write({'is_reconciled' : True})

                # else :
                #     line_ids = []
                #     move_line1 = {
                #         'name': 'Customer Reconcile' if record.payment_type == 'inbound' else 'Supplier Reconcile',
                #         # 'account_id': record.journal_id.default_account_id.id,
                #         'account_id': record.journal_id.default_account_id.id if record.payment_type == 'outbound' else record.destination_account_id.id,
                #         'currency_id': record.currency_id.id,
                #         'amount_currency': -record.amount,
                #         'debit': 0,
                #         'credit': record.amount,
                #         'partner_id': record.partner_id.id,
                #         'payment_id': record.id,
                #     }
                #     line_ids.append((0, 0, move_line1))
                #     move_line2 = {
                #         'name': 'Customer Reconcile' if record.payment_type == 'inbound' else 'Supplier Reconcile',
                #         # 'account_id': record.destination_account_id.id,
                #         'account_id': record.destination_account_id.id if record.payment_type == 'outbound' else record.journal_id.default_account_id.id,
                #         'currency_id': record.currency_id.id,
                #         'amount_currency': record.amount,
                #         'debit': record.amount,
                #         'credit': 0,
                #         'partner_id': record.partner_id.id,
                #         'payment_id': record.id,
                #     }
                #     line_ids.append((0, 0, move_line2))
                #     move_vals = {
                #         'journal_id': record.journal_id.id,
                #         'currency_id': record.currency_id.id,
                #         'date': fields.Date.today(), 
                #         'partner_id': record.partner_id.id,
                #         'branch_id': record.branch_id.id,
                #         'ref': record.move_id.ref,
                #         'line_ids': line_ids,
                #         'payment_id': record.id,
                #     }
                #     reconcile_move_id = move_obj.create(move_vals)
                #     reconcile_move_id.action_post()
                #     invoice_id = invoice.invoice_id
                #     # Get the lines to reconcile
                #     batches = self._get_batches(invoice_id)
                #     to_reconcile = []
                #     to_reconcile.append(batches[0]['lines'])

                #     domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                #     for lines in to_reconcile:
                #         payment_lines = reconcile_move_id.line_ids.filtered_domain(domain)
                #         # for account in payment_lines.account_id:
                #             # (payment_lines + lines).filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]).reconcile()
                #         for account in payment_lines.mapped('account_id'):
                #             lines_to_reconcile = (payment_lines + lines).filtered(lambda line: line.account_id == account and not line.reconciled)
                #             if lines_to_reconcile:
                #                 lines_to_reconcile.reconcile()
                # # record.write({'is_reconciled' : True, 'move_id': reconcile_move_id.id})
        return True      

    def _get_batches(self, invoices):
        ''' Group the account.move.line linked to the wizard together.
        :return: A list of batches, each one containing:
            * key_values:   The key as a dictionary used to group the journal items together.
            * moves:        An account.move recordset.
        '''
        self.ensure_one()
        # Keep lines having a residual amount to pay.
        available_lines = self.env['account.move.line']
        for line in invoices.line_ids:
            if line.move_id.state != 'posted':
                raise UserError(_("You can only register payment for posted journal entries."))

            if line.account_internal_type not in ('receivable', 'payable'):
                continue
            if line.currency_id:
                if line.currency_id.is_zero(line.amount_residual_currency):
                    continue
            else:
                if line.company_currency_id.is_zero(line.amount_residual):
                    continue
            available_lines |= line

        # Check.
        if not available_lines:
            raise UserError(
                _("You can't register a payment because there is nothing left to pay on the selected journal items."))
        if len(invoices.line_ids.company_id) > 1:
            raise UserError(_("You can't create payments for entries belonging to different companies."))
        if len(set(available_lines.mapped('account_internal_type'))) > 1:
            raise UserError(
                _("You can't register payments for journal items being either all inbound, either all outbound."))

        # res['line_ids'] = [(6, 0, available_lines.ids)]

        lines = available_lines

        if len(lines.company_id) > 1:
            raise UserError(_("You can't create payments for entries belonging to different companies."))
        if not lines:
            raise UserError(
                _("You can't open the register payment wizard without at least one receivable/payable line."))

        batches = {}
        payments = self.env['account.payment.register']
        for line in lines:
            batch_key = payments._get_line_batch_key(line)

            serialized_key = '-'.join(str(v) for v in batch_key.values())
            batches.setdefault(serialized_key, {
                'key_values': batch_key,
                'lines': self.env['account.move.line'],
            })
            batches[serialized_key]['lines'] += line
        return list(batches.values())
    

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        context = self._context
        if self._context.get('skip_account_move_synchronization', False):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            giro_id_ctx = self.env.context.get('active_id')
            giro_id = self.env['account.multipayment'].search([('id', '=', giro_id_ctx)])

            # if move.move_type == 'entry':
            #     move.write({'origin': pay.name})

            if giro_id.payment_type == 'giro':
                # if giro_id.state == 'post':
                if self.partner_type == 'supplier':
                    move_credit_lines = move.line_ids.filtered(lambda line: line.credit)
                    for line in move_credit_lines:
                        if line.account_id.id != pay.clearing_account_id.id:
                            line.write({'account_id': pay.clearing_account_id.id})


                if self.partner_type == 'customer':
                    move_debit_lines = move.line_ids.filtered(lambda line: line.debit)
                    for line in move_debit_lines:
                        if line.account_id.id != pay.clearing_account_id.id:
                            line.write({'account_id': pay.clearing_account_id.id})

                # if giro_id.state == 'cleared':
                #     if self.partner_type == 'supplier':
                #         move_credit_lines = move.line_ids.filtered(lambda line: line.credit)
                #         for line in move_credit_lines:
                #             if line.account_id.id != move.journal_id.default_account_id.id:
                #                 line.write({'account_id': move.journal_id.default_account_id.id})

                #     if self.partner_type == 'customer':
                #         move_debit_lines = move.line_ids.filtered(lambda line: line.debit)
                #         for line in move_debit_lines:
                #             if line.account_id.id != move.journal_id.default_account_id.id:
                #                 line.write({'account_id': move.journal_id.default_account_id.id})


            move_vals_to_write = {}
            payment_vals_to_write = {}
            line_ids_vals_to_write = []

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids

                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                if not liquidity_lines or len(liquidity_lines) != 1:
                # Handle the situation where there are no liquidity lines or multiple liquidity lines.
                # You may want to log a warning or handle it according to your business logic.
                    continue

                # if len(liquidity_lines) != 1 or len(counterpart_lines) != 1:
                #     raise UserError(_(
                #         "The journal entry %s reached an invalid state relative to its payment.\n"
                #         "To be consistent, the journal entry must always contains:\n"
                #         "- one journal item involving the outstanding payment/receipts account.\n"
                #         "- one journal item involving a receivable/payable account.\n"
                #         "- optional journal items, all sharing the same account.\n\n"
                #     ) % move.display_name)

                '''To allow multiple writeoff with different account'''
                #if writeoff_lines and len(writeoff_lines.account_id) != 1:
                #    raise UserError(_(
                #        "The journal entry %s reached an invalid state relative to its payment.\n"
                #        "To be consistent, all the write-off journal items must share the same account."
                #    ) % move.display_name)

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same currency."
                    ) % move.display_name)

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same partner."
                    ) % move.display_name)

                if counterpart_lines.account_id.user_type_id.type == 'receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency 

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id or counterpart_lines.currency_id.id or all_lines[0].currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id or counterpart_lines.partner_id.id or all_lines[0].partner_id.id,
                    'commercial_partner_id': liquidity_lines.partner_id.commercial_partner_id.id or counterpart_lines.partner_id.commercial_partner_id.id or all_lines[0].partner_id.commercial_partner_id.id,
                })

                payment_vals_to_write.update({
                    'amount': abs(liquidity_lines.amount_currency) or counterpart_lines.amount_currency or move.amount_total,
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id or counterpart_lines.currency_id.id or all_lines[0].currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id or counterpart_lines.partner_id.id or all_lines[0].partner_id.id,

                })
                if liquidity_amount > 0.0:
                    payment_vals_to_write.update({'payment_type': 'inbound'})
                elif liquidity_amount < 0.0:
                    payment_vals_to_write.update({'payment_type': 'outbound'})


            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))
            if self.env.context.get('default_payment_type') == 'giro':
                pay.write({'is_reconciled' : True})
            if giro_id.payment_type == 'giro':
                pay.write({'is_reconciled' : True})
                # pay._reconcile_payments()
            # if pay.is_reconciled == False:
                # pay._reconcile_payments()
                # pay._action_reconcile_payment()
            # if giro_id.state != 'cleared':
            #     pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))
    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        lines = super(AccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals)
        if self.analytic_group_ids:
            for line in lines:
                line['analytic_tag_ids'] = self.analytic_group_ids
        return lines 

    def _prepare_move_line_default_vals_custom(self, multiple_write_off_line_vals=[], administration=[]):
        '''This is a new function which is the custom of _prepare_move_line_default_vals.
        Prepare the dictionary to create the default account.move.lines for the current payment.
        :param of each item in multiple_write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        multiple_write_off_line_vals = multiple_write_off_line_vals or []
        
        administration = administration or []
        administration_account = administration and administration[0]['account_id'] or False

        if not self.journal_id.payment_debit_account_id or not self.journal_id.payment_credit_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set on the %s journal.",
                self.journal_id.display_name))
                
        #Administration Fee
        adm_amount_currency = 0
        for vals in administration:
            adm_amount_currency += abs(vals.get('amount', 0.0))

        # Compute amounts.
        write_off_amount_currency = 0
        for vals in multiple_write_off_line_vals:
            write_off_amount_currency += vals.get('amount', 0.0)

        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
            write_off_amount_currency *= -1
        else:
            liquidity_amount_currency = write_off_amount_currency = 0.0

        
        
        if self.active_manual_currency_rate:
            if self.apply_manual_currency_exchange:                
                write_off_balance = write_off_amount_currency / self.manual_currency_exchange_rate
                liquidity_balance = liquidity_amount_currency / self.manual_currency_exchange_rate
                adm_balance = adm_amount_currency / self.manual_currency_exchange_rate
            else:
                write_off_balance = self.currency_id._convert(write_off_amount_currency, self.company_id.currency_id, self.company_id, self.date)
                liquidity_balance = self.currency_id._convert(liquidity_amount_currency, self.company_id.currency_id, self.company_id, self.date)        
                adm_balance = self.currency_id._convert(adm_amount_currency, self.company_id.currency_id, self.company_id, self.date)
        else:
            write_off_balance = self.currency_id._convert(write_off_amount_currency, self.company_id.currency_id, self.company_id, self.date)
            liquidity_balance = self.currency_id._convert(liquidity_amount_currency, self.company_id.currency_id, self.company_id, self.date)        
            adm_balance = self.currency_id._convert(adm_amount_currency, self.company_id.currency_id, self.company_id, self.date)

        # If Liquidity amount less than Invoice amount (Less payment)
        # If Less payment, write_off_balance will be grater than zero (write_off_balance > 0)
        # If Liquidity amount greater than Invoice amount (overpayment)
        # If Overpayment, write_off_balance will be less than zero (write_off_balance < 0)
        overpayment = write_off_balance < 0 or False
        currency_id = self.currency_id.id
        counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
        counterpart_balance = -liquidity_balance - write_off_balance
        

        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                liquidity_line_name = _('Transfer to %s', self.journal_id.name)
            else: # payment.payment_type == 'outbound':
                liquidity_line_name = _('Transfer from %s', self.journal_id.name)
        else:
            liquidity_line_name = self.payment_reference

        # Compute a default label to set on the journal items.

        payment_display_name = {
            'outbound-customer': _("Customer Reimbursement"),
            'inbound-customer': _("Customer Payment"),
            'outbound-supplier': _("Vendor Payment"),
            'inbound-supplier': _("Vendor Reimbursement"),
        }

        default_line_name = self.env['account.move.line']._get_default_line_name(
            _("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
            self.amount,
            self.currency_id,
            self.date,
            partner=self.partner_id,
        )
        
        #Add the administriation fee to the payment total
        if liquidity_balance < 0:
            liquidity_balance += -adm_balance
        else:
            liquidity_balance += adm_balance
        liquidity_amount_currency += adm_amount_currency

        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name or default_line_name,
                'date_maturity': self.date,
                'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.journal_id.payment_credit_account_id.id if liquidity_balance < 0.0 else self.journal_id.payment_debit_account_id.id,
            },
            # Receivable / Payable.
            {
                'name': self.payment_reference or default_line_name,
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
            },
        ]
        
        if not self.currency_id.is_zero(adm_amount_currency):
            # Admistration Fee line
            line_vals_list.append({
                'name': _('Administration Fee'),
                'date_maturity': self.date,
                'amount_currency': adm_amount_currency if liquidity_balance < 0.0 else -adm_amount_currency,
                'currency_id': currency_id,
                'debit': adm_balance if liquidity_balance < 0.0 else 0.0,
                'credit': adm_balance if liquidity_balance > 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': administration_account,
            })
        
        if not self.currency_id.is_zero(write_off_amount_currency):
            # Write-off lines.
            if all(vals.get('amount', 0.00) > 0 for vals in multiple_write_off_line_vals) or all(vals.get('amount', 0.00) < 0 for vals in multiple_write_off_line_vals):
                for vals in multiple_write_off_line_vals:
                    amount = vals.get('amount', 0.00)
                    if self.payment_type == 'outbound' or (overpayment and amount > 0):
                        amount *= -1

                    if self.active_manual_currency_rate:
                        if self.apply_manual_currency_exchange:
                            write_off_amount = amount / self.manual_currency_exchange_rate
                        else:
                            write_off_amount = self.currency_id._convert(amount, self.company_id.currency_id, self.company_id, self.date)
                    else:
                        write_off_amount = self.currency_id._convert(amount, self.company_id.currency_id, self.company_id, self.date)


                    amt_currency = amount
                    debit_amt = write_off_amount if write_off_amount > 0.0 else 0.0
                    credit_amt = -write_off_amount if write_off_amount < 0.0 else 0.0
                    
                    line_vals_list.append({
                        'name': _("Difference Account - ") + vals.get('name') or default_line_name,
                        'amount_currency': amt_currency,
                        'currency_id': currency_id,
                        'debit': debit_amt,
                        'credit': credit_amt,
                        'partner_id': self.partner_id.id,
                        'account_id': vals.get('account_id'),
                    })
            else:
                for vals in multiple_write_off_line_vals:
                    amount = vals.get('amount', 0.00)
                    

                    if self.active_manual_currency_rate:
                        if self.apply_manual_currency_exchange:
                            write_off_amount = amount / self.manual_currency_exchange_rate
                        else:
                            write_off_amount = self.currency_id._convert(amount, self.company_id.currency_id, self.company_id, self.date)
                    else:
                        write_off_amount = self.currency_id._convert(amount, self.company_id.currency_id, self.company_id, self.date)
                    
                    if self.payment_type == 'outbound':
                        debit_amt  = -write_off_amount if write_off_amount < 0 else 0.00
                        credit_amt  = write_off_amount if write_off_amount > 0 else 0.00
                    else:
                        debit_amt  = write_off_amount if write_off_amount > 0 else 0.00
                        credit_amt  = -write_off_amount if write_off_amount < 0 else 0.00
                    amt_currency = debit_amt-credit_amt
                    
                    line_vals_list.append({
                        'name': _("Difference Account - ") + vals.get('name') or default_line_name,
                        'amount_currency': amt_currency,
                        'currency_id': currency_id,
                        'debit': debit_amt,
                        'credit': credit_amt,
                        'partner_id': self.partner_id.id,
                        'account_id': vals.get('account_id'),
                    })
        return line_vals_list
    
     
    @api.model_create_multi
    def create(self, vals_list):
        multiple_write_off_line_vals = []
        administration_fee_vals = []
        # Hack to add a custom write-off line.
        for vals in vals_list:
            if vals.get('administration_fee_vals',[]):
                administration_fee_vals += vals.pop('administration_fee_vals',None)
            elif vals.get('administration', False):
                administration_fee_vals = [{'name' : 'Admnistration Fee', 'amount' : vals.get('administration_fee',0), 'account_id' : vals.get('administration_account',False)}]
            
            if vals.get('multiple_write_off_line_vals',[]):
                multiple_write_off_line_vals += vals.pop('multiple_write_off_line_vals', None)
        
        if len(multiple_write_off_line_vals) > 0 or len(administration_fee_vals) > 0:
            payments = super(AccountPayment, self.with_context(multiple_write_off_line=True)).create(vals_list)

            for i, pay in enumerate(payments):
                to_write = {'payment_id': pay.id}
                for k, v in vals_list[i].items():
                    if k in self._fields and self._fields[k].store and k in pay.move_id._fields and pay.move_id._fields[k].store:
                        to_write[k] = v
                
                if 'line_ids' not in vals_list[i]:
                    line_ids = [(5, 0, 0)]
                    for line_vals in pay._prepare_move_line_default_vals_custom(multiple_write_off_line_vals=multiple_write_off_line_vals,administration=administration_fee_vals):
                        line_ids.append((0, 0, line_vals))
                    to_write['line_ids'] = line_ids
                pay.move_id.write(to_write)                
            return payments        
        else:
            return super(AccountPayment, self).create(vals_list)

class ApprovalMatrixAccountingLines(models.Model):
    _inherit = "approval.matrix.accounting.lines"

    receipt_id = fields.Many2one('account.payment', string='Payment')


class paymenSignatureHistory(models.Model):
    _name = 'payment.signature.history'
    
    payment_id = fields.Many2one('account.payment')
    approver_id = fields.Many2one('res.users')
    signature = fields.Binary(related="approver_id.digital_signature")
    timestamp = fields.Datetime(default=datetime.now())
    