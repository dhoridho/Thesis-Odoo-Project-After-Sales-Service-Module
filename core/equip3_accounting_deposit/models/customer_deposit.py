from odoo import tools, api, fields, models, _
from datetime import datetime, date, timedelta
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
from odoo.exceptions import UserError, ValidationError
from lxml import etree
import logging
import requests

_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json'}


class CustomerDeposit(models.Model):
    _name = 'customer.deposit'
    _description = 'Customer Deposit'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']


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
    def _domain_journal(self):
        active_company = self.env.company.id
        return [('type', 'in', ['bank', 'cash']), ('company_id', '=', active_company)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False)
    name = fields.Char(string="Name", readonly=True, tracking=True)
    is_deposit = fields.Boolean(string="Is Deposit")
    partner_id = fields.Many2one('res.partner', string="Customer", tracking=True, domain="[('is_customer', '=', True)]")
    is_customer = fields.Boolean(related="partner_id.is_customer", string="Is Customer")
    amount = fields.Monetary(currency_field='currency_id', string="Amount", tracking=True)
    communication = fields.Char(string="Reference", tracking=True)
    payment_date = fields.Date(string="Payment Date", tracking=True)
    remaining_amount = fields.Monetary(string="Remaining Amount", tracking=True, compute ='_compute_remaining_amount_deposit', store=True)
    return_deposit = fields.Many2one('account.move', string="Return Deposit", readonly=True, tracking=True, copy=False)
    deposit_reconcile_journal_id = fields.Many2one('account.journal', string="Deposit Reconcile Journal", tracking=True, domain=_domain_journal)
    journal_id = fields.Many2one('account.journal', string="Payment Method", tracking=True, domain=_domain_journal)
    deposit_account_id = fields.Many2one('account.account', string="Deposit Account", domain="[('type', '=', 'payable'), ('company_id', '=', company.id)]", tracking=True)
    filter_deposit_account_ids = fields.Many2many('account.account', string='Filter Depoist Account', compute='_compute_deposit_account_ids')
    currency_id = fields.Many2one('res.currency', string='Currency', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('rejected', 'Rejected'),
        ('post', 'Received'),
        ('posted', 'Posted'),
        ('returned', 'Returned'),
        ('converted', 'Converted to Revenue'),
        ('reconciled', 'Reconciled'),
        ('cancelled', 'Cancelled'),
    ], default='draft', track_visibility='onchange', copy=False, string="Status", tracking=True)
    deposit_move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True, tracking=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    suitable_journal_ids = fields.Many2many('account.journal', tracking=True)
    is_show_cancel = fields.Boolean(compute="_compute_show_cancel", string="Show Cancel")
    invoice_count = fields.Integer(compute="_compute_invoice", string='Invoices', copy=False, default=0)
    reconcile_count = fields.Integer(compute="_compute_reconcile", string='Invoices', copy=False, default=0,)
    reconcile_deposit_ids = fields.Many2many('account.move', 'reconcile_customer_deposit_rel', 'deposit_id', 'move_id', string="Reconciled", copy=False)
    invoice_deposit_ids = fields.Many2many('account.move', 'customer_deposit_invoice_rel', 'deposit_id', 'invoice_id', string="Invoiced", copy=False)
    approval_matrix_id = fields.Many2one('approval.matrix.accounting', string="Approval Matrix", compute='_get_approval_matrix')
    is_customer_deposit_approval_matrix = fields.Boolean(string="Is Customer Deposite Approval Matrix", compute='_get_approve_button_from_config')
    is_allowed_to_wa_notification_customer_deposit = fields.Boolean(string="Is Allowed to WA Notification Customer Deposit", compute='_get_approve_button_from_config')
    approved_matrix_ids = fields.One2many('approval.matrix.accounting.lines', 'customer_deposit_id', string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.accounting.lines', string='Approval Matrix Line', compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    state1 = fields.Selection(related="state", tracking=False)
    state2 = fields.Selection(related="state", tracking=False)
    request_partner_id = fields.Many2one('res.partner', string="Requested Partner")
    deposit_history = fields.Many2many('account.move', 'cust_deposit_history_rel', 'deposit_id', 'move_id', string="Deposit History", readonly=True, tracking=True, copy=False)
    add_amount_approver = fields.Monetary(currency_field='currency_id', string="Add Amount", tracking=True)    
    approve_add_amount = fields.Boolean(string="Approva add amount",default=False)
    deposit_count = fields.Integer(string='Request for Approval')
    convert_to_revenue_move_id = fields.Many2one('account.move', string="Convert to Revenue", readonly=True, tracking=True, copy=False)
    deposit_return_ids = fields.Many2many('account.move', 'cust_deposit_return_ids_rel', 'deposit_id', 'move_id', string="Deposit return", readonly=True, copy=False)
    move_ids = fields.Many2many('account.move', 'cust_deposit_move_ids_rel', 'deposit_id', 'move_id', string="Move Ids", readonly=True, copy=False)
    deposit_line_history = fields.One2many('customer.deposit.line.history', 'customer_deposit_id', string='Deposit History', readonly=True, copy=False)
    analytic_group_ids = fields.Many2many('account.analytic.tag', domain="[('company_id', '=', company_id)]", string="Analytic Group", copy=False)

    @api.constrains('amount')
    def _check_values_of_amount(self):
        if self.amount <= 0 :
            raise ValidationError("Deposit amount must be greater than 0.")

    @api.constrains('deposit_reconcile_journal_id', 'journal_id')
    def _check_journalid(self):
        if self.journal_id.type not in ['bank', 'cash']:
            raise ValidationError("Please select Journal Cash or Bank")
        if self.deposit_reconcile_journal_id.type  not in ['bank', 'cash']:
            raise ValidationError("Please select Journal Cash or Bank")

    def _send_wa_reject_customer_deposit(self, submitter, phone_num, created_date, approver = False, reason = False):
        wa_template = self.env.ref('equip3_accounting_deposit.wa_template_new_rejection_customer_deposit_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var = [{'variable' : '{submitter_name}', 'value' : submitter},
                                {'variable' : '{approver_name}', 'value' : approver},
                               {'variable' : '{create_date}', 'value' : created_date},
                                 {'variable' : '{feedback}', 'value' : reason}]

                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone_num))
            else:
                raise ValidationError(_("Broadcast Template not found!"))
    
    def _send_wa_approval_customer_deposit(self, approver, phone_num, created_date, submitter):
        wa_template = self.env.ref('equip3_accounting_deposit.wa_template_new_approval_customer_deposit_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var = [{'variable' : '{approver_name}', 'value' : approver.name},
                               {'variable' : '{submitter_name}', 'value' : submitter},
                                {'variable' : '{create_date}', 'value' : created_date},]
                
                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone_num))
            else:
                raise ValidationError(_("Broadcast Template not found!"))


    def action_approve(self):
        for record in self:
            action_id = self.env.ref('equip3_accounting_deposit.action_customer_deposit')
            template_id = self.env.ref('equip3_accounting_deposit.email_template_customer_deposit_approval_matrix')
            template_id_submitter = self.env.ref('equip3_accounting_deposit.email_template_customer_deposit_submitter_approval_matrix')
            # wa_template_id = self.env.ref('equip3_accounting_deposit.wa_template_customer_deposit_approval_matrix')
            # wa_template_id_submitter = self.env.ref('equip3_accounting_deposit.wa_template_customer_deposit_submitter_approval_matrix')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=customer.deposit'
            created_date = record.create_date.date()
            user = self.env.user
            currency = ''
            if record.currency_id.position == 'before':
               currency = record.currency_id.symbol + str(record.amount)
            else:
                currency = str(record.amount) + ' ' + record.currency_id.symbol
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                        user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (self.env.user.name, local_datetime)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True})
                        next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : approving_matrix_line_user.partner_id.email,
                                    'approver_name' : approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter' : self.env.user.name,
                                    'url' : url,
                                    "due_date": record.payment_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                    "currency": currency,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                phone_num = str(approving_matrix_line_user.mobile or approving_matrix_line_user.partner_id.mobile)
                                if self.is_allowed_to_wa_notification_customer_deposit:
                                    record._send_wa_approval_customer_deposit(approving_matrix_line_user, phone_num, created_date, submitter=self.env.user.name)
                                # record._send_whatsapp_message(wa_template_id, approving_matrix_line_user, currency, url)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                    'approver_name' : next_approval_matrix_line_id[0].user_ids[0].name,
                                    'date': date.today(),
                                    'submitter' : self.env.user.name,
                                    'url' : url,
                                    "due_date": record.payment_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                    "currency": currency,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                phone_num = str(next_approval_matrix_line_id[0].user_ids[0].mobile or next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile)
                                # record._send_whatsapp_message(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], currency, url)
                                if self.is_allowed_to_wa_notification_customer_deposit:
                                    record._send_wa_approval_customer_deposit(next_approval_matrix_line_id[0].user_ids[0], phone_num, created_date, submitter=self.env.user.name)
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                record.customer_deposit_post()
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.request_partner_id.email,
                    'approver_name' : record.name,
                    'date': date.today(),
                    'create_date': record.create_date.date(),
                    'submitter' : self.env.user.name,
                    'url' : url,
                    "due_date": record.payment_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                    "currency": currency,
                }
                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                phone_num = str(record.request_partner_id.mobile)
                if self.is_allowed_to_wa_notification_customer_deposit:
                    record._send_wa_approval_customer_deposit(record.request_partner_id, phone_num, created_date, submitter=self.env.user.name)
                # record._send_whatsapp_message(wa_template_id_submitter, record.request_partner_id.user_ids, currency, url)

    @api.depends('amount', 'company_id', 'branch_id')
    def _get_approval_matrix(self):
        for record in self:
            matrix_id = False
            matrix_id = self.env['approval.matrix.accounting'].search([
                ('company_id', '=', record.company_id.id),
                ('branch_id', '=', record.branch_id.id),
                ('min_amount', '<=', record.amount),
                ('max_amount', '>=', record.amount),
                ('approval_matrix_type', '=', 'customer_deposit_approval_matrix')
            ], limit=1)
            record.approval_matrix_id = matrix_id
            record._compute_approving_matrix_lines()

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Deposit ',
            'res_model': 'customer.deposit.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_add_amount_deposit(self):
        context = dict(self.env.context) or {}
        context.update({'active_model': 'customer.deposit','active_ids': self.ids})
        action = {
                    'type': 'ir.actions.act_window',
                    'name': 'Add Amount Customer Deposit',
                    'res_model': 'cust.deposit.amount.wizard',
                    'view_mode': 'form,tree',
                    'target': 'new',
                    'context': context,
                 }
        return action

    # @api.model
    # def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
    #     domain = domain or []
    #     domain.extend([('company_id', 'in', self.env.companies.ids)])
    #     return super(CustomerDeposit, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    # @api.model
    # def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
    #     domain = domain or []
    #     domain.extend([('company_id', '=', self.env.companies.ids)])
    #     return super(CustomerDeposit, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit,
    #                                                             orderby=orderby, lazy=lazy)

    @api.onchange('approval_matrix_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.state == 'draft' and record.is_customer_deposit_approval_matrix:
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

    def _send_wa_request_for_approval_customer_deposit(self, approver, phone_num, currency, url, submitter):
        wa_template = self.env.ref('equip3_accounting_deposit.wa_template_new_request_approval_customer_deposit_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var = [{'variable' : '{approver_name}', 'value' : approver.name},
                               {'variable' : '{submitter_name}', 'value' : submitter},
                                {'variable' : '{url}', 'value' : url},]
                
                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone_num))
            else:
                raise ValidationError(_("Broadcast Template not found!"))

    def action_request_for_approval(self):
        for record in self:
            action_id = self.env.ref('equip3_accounting_deposit.action_customer_deposit')
            template_id = self.env.ref('equip3_accounting_deposit.email_template_customer_deposit_approval_matrix')
            # wa_template_id = self.env.ref('equip3_accounting_deposit.wa_template_customer_deposit_approval_matrix')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=customer.deposit'
            currency = ''
            if record.currency_id.position == 'before':
               currency = record.currency_id.symbol + ' ' + str(record.amount)
            else:
                currency = str(record.amount) + ' ' + record.currency_id.symbol
            record.request_partner_id = self.env.user.partner_id.id
            if record.approved_matrix_ids and len(record.approved_matrix_ids[0].user_ids) > 1:
                for approved_matrix_id in record.approved_matrix_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.partner_id.email,
                        'approver_name' : approver.name,
                        'date': date.today(),
                        'submitter' : self.env.user.name,
                        'url' : url,
                        "due_date": record.payment_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                        "currency": currency,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    phone_num = str(approver.mobile or approver.partner_id.mobile)
                    if self.is_allowed_to_wa_notification_customer_deposit:
                        record._send_wa_request_for_approval_customer_deposit(approver, phone_num, currency, url, submitter=self.env.user.name)
                    # record._send_whatsapp_message(wa_template_id, approver, currency, url)
            else:
                approver = record.approved_matrix_ids[0].user_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : approver.partner_id.email,
                    'approver_name' : approver.name,
                    'date': date.today(),
                    'submitter' : self.env.user.name,
                    'url' : url,
                    "due_date": record.payment_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                    "currency": currency,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                phone_num = str(approver.mobile or approver.partner_id.mobile)
                # record._send_whatsapp_message(wa_template_id, approver, currency, url)
                if self.is_allowed_to_wa_notification_customer_deposit:
                    record._send_wa_request_for_approval_customer_deposit(approver, phone_num, currency, url, submitter=self.env.user.name)
            record.write({'state': 'to_approve'})


    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved),
                                 key=lambda r: r.sequence)
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

    def _get_approve_button_from_config(self):
        for record in self:
            # is_customer_deposit_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_customer_deposit_approval_matrix', False)
            # record.is_customer_deposit_approval_matrix = is_customer_deposit_approval_matrix
            record.is_customer_deposit_approval_matrix = self.env['accounting.config.settings'].search([], limit=1).is_allow_customer_deposit_approval_matrix
            record.is_allowed_to_wa_notification_customer_deposit = self.env['accounting.config.settings'].search([], limit=1).is_allow_customer_deposit_wa_notification

    @api.onchange('journal_id')
    def currency(self):
        self._get_approve_button_from_config()
        for rec in self:
            if rec.journal_id:
                rec.currency_id = rec.journal_id.currency_id

    @api.onchange('name')
    def onchange_name(self):
        self._compute_deposit_account_ids()

    
    @api.depends('company_id')
    def _compute_deposit_account_ids(self):
        payable_type_id = self.env.ref('account.data_account_type_payable')
        account_ids = self.env['account.account'].search([('user_type_id', '=', payable_type_id.id)]).ids
        for record in self:
            record.filter_deposit_account_ids = [(6, 0, account_ids)]

    @api.depends('amount', 'remaining_amount')
    def _compute_show_cancel(self):
        for record in self:
            if record.amount == record.remaining_amount:
                record.is_show_cancel = True
            else: 
                record.is_show_cancel = False

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('customer.deposit')
        return super(CustomerDeposit, self).create(vals)

    def customer_deposit_post(self):
        for record in self:
            record.write({'state': 'post'})
            ref = 'Customer Deposit ' + (record.name or '')
            name = 'Customer Deposit ' + (record.name or '')
            # currency = self.env['res.currency'].search([('id', '=', record.currency_id.id)], limit=1)
            currency = record.currency_id
            company_currency = record.company_id.currency_id
            if currency == company_currency:
                debit_vals = {
                    'debit': abs(record.amount),
                    'date': record.payment_date,
                    'name': name,
                    'credit': 0.0,
                    'account_id': record.journal_id.payment_debit_account_id.id,
                    'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    'partner_id': record.partner_id.id,
                    'customer_deposit_id': record.id,
                }
                credit_vals = {
                    'debit': 0.0,
                    'date': record.payment_date,
                    'name': name,
                    'credit': abs(record.amount),
                    'account_id': record.deposit_account_id.id,
                    'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    'partner_id': record.partner_id.id,
                    'customer_deposit_id': record.id,
                }
                vals = {
                    'ref': ref,
                    'date': record.payment_date,
                    'journal_id': record.journal_id.id,
                    'analytic_group_ids': [(6, 0, record.analytic_group_ids.ids)],
                    'partner_id': record.partner_id.id,
                    'branch_id': record.branch_id.id,
                    'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
                }
            else:
                currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', record.currency_id.id), ('name', '=', record.payment_date.strftime(DEFAULT_SERVER_DATE_FORMAT))], limit=1)
                amount = record.currency_id._convert(abs(record.amount), record.company_id.currency_id, record.company_id, record.payment_date,)
                debit_vals = {
                    'amount_currency' : record.amount,
                    'debit': abs(record.amount / currency_rate.rate) if currency_rate else amount,
                    'date': record.payment_date,
                    'name': name,
                    'credit': 0.0,
                    'account_id': record.journal_id.payment_debit_account_id.id,
                    'partner_id': record.partner_id.id,
                    'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    'customer_deposit_id': record.id,
                    'currency_id': record.currency_id.id,
                }
                credit_vals = {
                    'debit': 0.0,
                    'date': record.payment_date,
                    'name': name,
                    'amount_currency' : -record.amount,
                    'credit': abs(record.amount / currency_rate.rate) if currency_rate else amount,
                    'account_id': record.deposit_account_id.id,
                    'partner_id': record.partner_id.id,
                    'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    'customer_deposit_id': record.id,
                    'currency_id': record.currency_id.id,
                }
                vals = {
                    'ref': ref,
                    'currency_id': record.currency_id.id,
                    'date': record.payment_date,
                    'journal_id': record.journal_id.id,
                    'partner_id': record.partner_id.id,
                    'analytic_group_ids': [(6, 0, record.analytic_group_ids.ids)],
                    'branch_id': record.branch_id.id,
                    'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
                }
            move_id = self.env['account.move'].create(vals)
            move_id.post()
            record.deposit_move_id = move_id.id

    def convert_revenue(self):
        context = dict(self.env.context) or {}
        context.update({'default_deposit_type': 'customer_deposit'})
        return {
            'name': 'Customer Deposit',
            'type': 'ir.actions.act_window',
            'res_model': 'convert.revenue',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def button_cancel_customer_deposit(self):
        for record in self:
            if record.amount != record.remaining_amount:
                raise ValidationError(
                    _("Cannot cancel Deposit! There are already transaction reconcile with this deposit."))
            else:
                record.deposit_move_id.button_draft()
                record.deposit_move_id.button_cancel()
                record.write({'state': 'cancelled'})

    def button_draft_customer_deposit(self):
        for payment in self:
            payment.write({'state': 'draft'})
        return True

    @api.constrains('amount')
    def _check_values_of_amount(self):
        if self.amount <= 0:
            raise ValidationError("Deposit amount must be greater than 0.")

    def _check_invoice(self,invoices):
        invoice_partials = []
        for invoice in invoices:
            pay_term_lines = invoice.line_ids.filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))            
            for partial in pay_term_lines.matched_debit_ids:
                invoice_partials.append((partial.debit_move_id.move_id))
            for partial in pay_term_lines.matched_credit_ids:
                invoice_partials.append((partial.credit_move_id.move_id))
        return invoice_partials

    @api.depends('invoice_deposit_ids')
    def _compute_invoice(self):
        for rec in self:
            for invoice_deposit_id in rec.invoice_deposit_ids:
                chek_inv = self._check_invoice(invoice_deposit_id)
                remove_inv = True
                for inv in chek_inv:
                    check_reconcile = rec.reconcile_deposit_ids.filtered(lambda line: line.id == inv.id)
                    if check_reconcile:
                        remove_inv = False
                if remove_inv:
                    rec.write({'invoice_deposit_ids' : [(3,invoice_deposit_id.id)]})
            rec.invoice_count = len(rec.invoice_deposit_ids)
            if rec.remaining_amount > 0 and rec.invoice_deposit_ids:
                rec.state = 'post'

    @api.depends('reconcile_deposit_ids')
    def _compute_reconcile(self):
        for rec in self:
            for reconcile_deposit_id in rec.reconcile_deposit_ids:
                remove_deposit = True
                chek_inv = self._check_invoice(rec.invoice_deposit_ids)
                for inv in chek_inv:
                    if inv.id == reconcile_deposit_id.id:
                        remove_deposit = False
                if remove_deposit:
                    reconcile_deposit_id.button_draft()
                    reconcile_deposit_id.button_cancel()
                    rec.write({'reconcile_deposit_ids' : [(3,reconcile_deposit_id.id)]})
            rec.reconcile_count = len(rec.reconcile_deposit_ids)
            if rec.remaining_amount > 0 and rec.reconcile_deposit_ids:
                rec.state = 'post'

    @api.depends('amount', 'deposit_move_id', 'deposit_history', 'invoice_deposit_ids','reconcile_deposit_ids', 'deposit_return_ids', 'return_deposit', 'convert_to_revenue_move_id')
    def _compute_remaining_amount_deposit(self):
        for rec in self:
            total_deposit_history = sum(rec.deposit_history.mapped('amount_total_signed')) or 0.0
            total_deposit_move_id = 0
            list_move_ids = []
            list_move_ids = list_move_ids + rec.deposit_move_id.ids + rec.deposit_history.ids+ rec.deposit_return_ids.ids + rec.return_deposit.ids  + rec.reconcile_deposit_ids.ids + rec.convert_to_revenue_move_id.ids
            list_move_ids.sort(reverse=True)
            rec.write({'move_ids' : [(6, 0, list_move_ids)],
                       'deposit_line_history' : [(5,0,0)]
                       })
            move_line = []
            if rec.move_ids:
                for move_id in rec.move_ids:
                    total_amount = -move_id.amount_total_signed
                    check_move_deposit = rec.deposit_move_id.filtered(lambda line: line.id == move_id.id)
                    if check_move_deposit:
                        total_amount = move_id.amount_total_signed
                    
                    check_move_total_deposit = rec.deposit_history.filtered(lambda line: line.id == move_id.id)
                    if check_move_total_deposit:
                        total_amount = move_id.amount_total_signed                
                    tmp_line = {
                                    'move_id' : move_id.id,
                                    'amount_total_signed' : total_amount,
                                }
                    move_line.append((0,0,tmp_line))
                rec.write({'deposit_line_history' : move_line})
            if rec.deposit_move_id:
                total_deposit_move_id = rec.deposit_move_id.amount_total_signed
                rec.amount = total_deposit_move_id + total_deposit_history
            else:
                total_deposit_move_id = rec.amount
            rec.remaining_amount = sum(rec.deposit_line_history.mapped('amount_total_signed')) if rec.deposit_line_history else total_deposit_move_id
            if rec.remaining_amount > 0 and rec.reconcile_deposit_ids:
                rec.state = 'post'

    def action_view_invoice(self):
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('account.view_out_invoice_tree').id, 'tree'), (False, 'form')],
            'context': {'default_move_type': 'out_invoice'},
            'target': 'current',
            'domain': [('move_type', '=', 'out_invoice'), ('id', 'in', self.invoice_deposit_ids.ids)]
        }

    def action_view_reconcile(self):
        return {
            'name': _('Reconciles'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('account.view_move_tree').id, 'tree'), (False, 'form')],
            'context': {'default_move_type': 'entry', 'search_default_misc_filter': 1, 'view_no_maturity': True},
            'target': 'current',
            'domain': [('id', 'in', self.reconcile_deposit_ids.ids)]
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
        # sys.setdefaultencoding("utf-8")
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
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def action_view_list_approval(self):
        return {
            'name': _('List Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'customer.deposit.approval.line',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('customer_deposit_id', 'in', self.ids),('approve', '=', False)]
        }

class CustomerDepositLineHistory(models.Model):
    _name = 'customer.deposit.line.history'
    _description = 'Customer Deposit History'

    customer_deposit_id = fields.Many2one('customer.deposit', string='Customer Deposit')
    move_id = fields.Many2one('account.move', string='Journal Entries')
    name = fields.Char(string='Name', related='move_id.name')
    date = fields.Date(string='Date', related='move_id.date')
    ref = fields.Char(string='References', related='move_id.ref')
    state = fields.Selection(string='State', related='move_id.state')
    amount_total_signed = fields.Float(string='Amount')

class CustomerDepositApprovalLine(models.Model):
    _name = 'customer.deposit.approval.line'
    _description = 'List Approval'

    customer_deposit_id = fields.Many2one('customer.deposit', string='Customer Deposit')
    name = fields.Char(string='Name', related='customer_deposit_id.name')
    date = fields.Date(string='Date')
    amount = fields.Float(string='Amount')
    approve = fields.Boolean(string='Approve', default=False)

    def action_approve(self):
        for list_approval in self:
            for record in list_approval.customer_deposit_id:
                action_id = self.env.ref('equip3_accounting_deposit.action_customer_deposit')
                template_id = self.env.ref('equip3_accounting_deposit.email_template_customer_deposit_approval_matrix')
                template_id_submitter = self.env.ref('equip3_accounting_deposit.email_template_customer_deposit_submitter_approval_matrix')
                wa_template_id = self.env.ref('equip3_accounting_deposit.wa_template_customer_deposit_approval_matrix')
                wa_template_id_submitter = self.env.ref('equip3_accounting_deposit.wa_template_customer_deposit_submitter_approval_matrix')
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=customer.deposit'
                created_date = record.create_date.date()
                user = self.env.user
                currency = ''
                if record.currency_id.position == 'before':
                   currency = record.currency_id.symbol + str(record.amount)
                else:
                    currency = str(record.amount) + ' ' + record.currency_id.symbol
                if record.is_approve_button and record.approval_matrix_line_id:
                    approval_matrix_line_id = record.approval_matrix_line_id
                    if user.id in approval_matrix_line_id.user_ids.ids and \
                            user.id not in approval_matrix_line_id.approved_users.ids:
                        name = approval_matrix_line_id.state_char or ''
                        utc_datetime = datetime.now()
                        local_timezone = pytz.timezone(self.env.user.tz)
                        local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                        local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        if name != '':
                            name += "\n • %s: Approved - %s" % (self.env.user.name, local_datetime)
                        else:
                            name += "• %s: Approved - %s" % (self.env.user.name, local_datetime)

                        approval_matrix_line_id.write({
                            'last_approved': self.env.user.id, 'state_char': name,
                            'approved_users': [(4, user.id)]})
                        if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                            approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True})
                            next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                            if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                                for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                    ctx = {
                                        'email_from' : self.env.user.company_id.email,
                                        'email_to' : approving_matrix_line_user.partner_id.email,
                                        'approver_name' : approving_matrix_line_user.name,
                                        'date': date.today(),
                                        'submitter' : self.env.user.name,
                                        'url' : url,
                                        "due_date": record.payment_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                        "currency": currency,
                                    }
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                    phone_num = approving_matrix_line_user.partner_id.mobile
                                    if record.is_allowed_to_wa_notification_customer_deposit:
                                        record._send_wa_approval_customer_deposit(approving_matrix_line_user, phone_num, created_date, submitter=self.env.user.name)
                                    # record._send_whatsapp_message(wa_template_id, approving_matrix_line_user, currency, url)
                            else:
                                if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                    ctx = {
                                        'email_from' : self.env.user.company_id.email,
                                        'email_to' : next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                        'approver_name' : next_approval_matrix_line_id[0].user_ids[0].name,
                                        'date': date.today(),
                                        'submitter' : self.env.user.name,
                                        'url' : url,
                                        "due_date": record.payment_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                        "currency": currency,
                                    }
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                    phone_num = next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile
                                    if record.is_allowed_to_wa_notification_customer_deposit:
                                        record._send_wa_approval_customer_deposit(next_approval_matrix_line_id[0].user_ids[0], phone_num, created_date, submitter=self.env.user.name)
                                    # record._send_whatsapp_message(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], currency, url)
                if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                    list_approval.action_confirm()
                    record.write({'deposit_count': record.deposit_count-1})
                    # record.write({'add_amount_approver': amount_approver, 'approve_add_amount': approve_add_amount, 'deposit_count': record.deposit_count-1})
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : record.request_partner_id.email,
                        'approver_name' : record.name,
                        'date': date.today(),
                        'create_date': record.create_date.date(),
                        'submitter' : self.env.user.name,
                        'url' : url,
                        "due_date": record.payment_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                        "currency": currency,
                    }
                    template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                    phone_num = record.request_partner_id.mobile
                    if record.is_allowed_to_wa_notification_customer_deposit:
                        record._send_wa_approval_customer_deposit(record.request_partner_id, phone_num, created_date, submitter=self.env.user.name)
                    # record._send_whatsapp_message(wa_template_id_submitter, record.request_partner_id.user_ids, currency, url)
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'customer.deposit',
                'view_mode': 'form',
                'res_id': list_approval.customer_deposit_id.id,
            }
            return action

    def action_confirm(self):
        for list_approval in self:
            for customer_deposit_id in list_approval.customer_deposit_id:
                debit_vals = {
                    'partner_id': customer_deposit_id.partner_id.id,
                    'name': customer_deposit_id.journal_id.payment_debit_account_id.name,
                    'analytic_tag_ids': [(6, 0, customer_deposit_id.analytic_group_ids.ids)],
                    'account_id': customer_deposit_id.journal_id.payment_debit_account_id.id,
                    'currency_id': customer_deposit_id.currency_id.id,
                    'date': list_approval.date,
                    'debit': abs(list_approval.amount),
                    'credit': 0.0,
                }
                credit_vals = {
                    'partner_id': customer_deposit_id.partner_id.id,
                    'name': customer_deposit_id.deposit_account_id.name,
                    'analytic_tag_ids': [(6, 0, customer_deposit_id.analytic_group_ids.ids)],
                    'account_id': customer_deposit_id.deposit_account_id.id,
                    'currency_id': customer_deposit_id.currency_id.id,
                    'date': list_approval.date,
                    'debit': 0.0,
                    'credit': abs(list_approval.amount),
                }
                vals = {
                    'ref': 'Add Amount Customer Deposit ' + customer_deposit_id.name,
                    'partner_id': customer_deposit_id.partner_id.id,
                    'currency_id': customer_deposit_id.currency_id.id,
                    'date': list_approval.date,
                    'journal_id': customer_deposit_id.journal_id.id,
                    'analytic_group_ids': [(6, 0, customer_deposit_id.analytic_group_ids.ids)],
                    'branch_id': customer_deposit_id.branch_id.id,
                    'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
                }
                move_id = self.env['account.move'].create(vals)
                move_id.post()
                customer_deposit_id.deposit_history += move_id
                list_approval.write({'approve' : True})

    def action_reject(self):
        context = dict(self.env.context) or {}
        context.update({'active_model': 'customer.deposit','active_ids': self.customer_deposit_id.ids, 'id_approval': self.id})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Deposit ',
            'res_model': 'customer.deposit.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

class AccountMove(models.Model):
    _inherit = 'account.move'

    customer_deposit_ids = fields.Many2many('customer.deposit', 'customer_deposit_invoice_rel', 'invoice_id',
                                            'deposit_id', string="Customer Deposit")
    vendor_deposit_ids = fields.Many2many('vendor.deposit', 'vendor_deposit_invoice_rel', 'invoice_id', 'deposit_id',
                                          string="Vendor Deposit")


class ApprovalMatrixAccountingLines(models.Model):
    _inherit = "approval.matrix.accounting.lines"

    customer_deposit_id = fields.Many2one('customer.deposit', string='Account Customer Deposit')

