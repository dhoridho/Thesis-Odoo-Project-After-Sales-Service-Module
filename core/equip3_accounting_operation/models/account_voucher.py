import pytz
from pytz import timezone, UTC
from odoo import fields, models, api, _
from odoo.addons import decimal_precision as dp
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, ValidationError
from num2words import num2words
import logging
import requests
import json
import base64
from ast import literal_eval
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam


class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    @api.model
    def create(self, vals):
        records = super(AccountVoucher, self).create(vals)
        for record in records:
            if record.voucher_type == 'sale':
                number = self.env['ir.sequence'].next_by_code(
                    'seq.account.voucher.oin')
                record.number = number
            elif record.voucher_type == 'purchase':
                number = self.env['ir.sequence'].next_by_code(
                    'seq.account.voucher.oex')
                record.number = number
        return records

    untax_amount = fields.Monetary(readonly=True,
                                   store=True,
                                   compute='_compute_total')
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
    def _domain_partner_id(self):
        domain = [('company_id','in',[self.env.company.id, False]),('parent_id','=',False)]
        voucher_type = self._context.get('default_voucher_type') or False
        if voucher_type:
            if voucher_type == 'sale':
                domain += [('is_customer','=',True)]
            elif voucher_type == 'purchase':
                domain += [('is_vendor','=',True)]
        return domain

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)
    approval_matrix_id = fields.Many2one('approval.matrix.accounting', string="Approval Matrix",
                                         compute='_get_approval_matrix')
    is_other_income_approval_matrix = fields.Boolean(string="Is Other Income/Expense Approval Matrix",
                                                     compute='_get_approve_button_from_config')
    is_allowed_to_wa_notification = fields.Boolean(string="Is Allowed WA Notification", compute='_get_approve_button_from_config')
    approved_matrix_ids = fields.One2many(
        'approval.matrix.accounting.lines', 'voucher_id', string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.accounting.lines', string='Approval Matrix Line',
                                              compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(
        string='Is Approve Button', compute='_get_approve_button', store=False)
    state = fields.Selection(selection_add=[
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('posted',)
    ], ondelete={'to_approve': 'cascade', 'approved': 'cascade', 'rejected': 'cascade'})
    state1 = fields.Selection(related="state", tracking=False)
    state2 = fields.Selection(related="state", tracking=False)
    analytic_group_ids = fields.Many2many('account.analytic.tag',  domain="[('company_id', '=', company_id)]",
                                          string="Analytic Group")
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    company_id = fields.Many2one("res.company",
                                 string="Company",
                                 default=lambda self: self.env.company)
    request_partner_id = fields.Many2one(
        'res.partner', string="Requested Partner")
    partner_id = fields.Many2one('res.partner', domain=_domain_partner_id)
    
    @api.onchange('analytic_group_ids')
    def set_analytic_group_ids(self):
        for res in self:
            for line in res.line_ids:
                line.update(
                    {'analytic_tag_ids': [(6, 0, res.analytic_group_ids.ids)], })

    @api.depends('amount', 'company_id', 'branch_id')
    def _get_approval_matrix(self):
        for record in self:
            if record.voucher_type == "sale":
                matrix_id = self.env['approval.matrix.accounting'].search([
                    ('company_id', '=', record.company_id.id),
                    ('branch_id', '=', record.branch_id.id),
                    ('min_amount', '<=', record.amount),
                    ('max_amount', '>=', record.amount),
                    ('approval_matrix_type', '=', 'other_income')
                ], limit=1)
            elif record.voucher_type == "purchase":
                matrix_id = self.env['approval.matrix.accounting'].search([
                    ('company_id', '=', record.company_id.id),
                    ('branch_id', '=', record.branch_id.id),
                    ('min_amount', '<=', record.amount),
                    ('max_amount', '>=', record.amount),
                    ('approval_matrix_type', '=', 'other_expense')
                ], limit=1)
            record.approval_matrix_id = matrix_id
            record._compute_approving_matrix_lines()

    def _get_approve_button_from_config(self):
        for record in self:
            # is_other_income_approval_matrix = False
            if record.voucher_type == 'sale':
                # is_other_income_approval_matrix = self.env['ir.config_parameter'].sudo().get_param(
                #     'is_other_income_approval_matrix', False)
                is_other_income_approval_matrix = self.env['accounting.config.settings'].search([], limit=1).is_allow_other_income_approval_matrix
                is_allowed_to_wa_notification = self.env['accounting.config.settings'].search([], limit=1).is_allow_other_income_wa_notification
            elif record.voucher_type == 'purchase':
                # is_other_income_approval_matrix = self.env['ir.config_parameter'].sudo().get_param(
                #     'is_other_expense_approval_matrix', False)
                is_other_income_approval_matrix = self.env['accounting.config.settings'].search([], limit=1).is_allow_other_expense_approval_matrix
                is_allowed_to_wa_notification = self.env['accounting.config.settings'].search([], limit=1).is_allow_other_expense_wa_notification
            record.is_other_income_approval_matrix = is_other_income_approval_matrix
            record.is_allowed_to_wa_notification = is_allowed_to_wa_notification

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

    @api.onchange('approval_matrix_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.state == 'draft' and record.is_other_income_approval_matrix:
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
        exceeding_lines = []
        for line in self.line_ids:
            remaining_amounts = self.env['crossovered.budget'].search([
                ('company_id', '=', line.company_id.id),
                ('account_tag_ids', 'in', line.analytic_tag_ids.ids),  # Added comma here
                ('date_from', '<=', line.voucher_id.account_date),
                ('date_to', '>=', line.voucher_id.account_date)
                ])
            if remaining_amounts:
                subtotal_without_tax = 0
                for line2 in self.line_ids:
                    if line2.account_id.id == line.account_id.id:
                        subtotal_without_tax += (line2.price_unit * line2.quantity)
                # subtotal_without_tax = line.price_unit * line.quantity
                if line.expense_budget != 0 and subtotal_without_tax > line.expense_budget:
                    exceeding_lines.append(line)  # Append the line record itself

        # Step 2: The list comprehension now works correctly with line records
        if exceeding_lines:
            wizard = self.env['expense.request.warning'].create({
                'warning_line_ids': [
                    (0, 0, {
                        'product_id': line.product_id.id,
                        'budgetary_position_id': line.budgetary_position_id.id,
                        'account_id': line.account_id.id,
                        'expense_budget': round(line.expense_budget, 2) if line.expense_budget else 0.0,
                        'planned_budget': round(line.planned_budget, 2) if line.planned_budget else 0.0,
                        'realized_amount': round((line.price_unit * line.quantity)),
                    }) for line in exceeding_lines
                ]
            })
            return {
                'name': 'Expense Request Warning',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'expense.request.warning',
                'res_id': wizard.id,
                'target': 'new',
            }
        else:
            self.send_request_for_approval()

    def _send_wa_reject_other_income_expense(self, submitter, phone_num, created_date, approver = False, reason = False):
        if self.voucher_type == 'sale':
            wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_rejection_other_income_1')
        elif self.voucher_type == 'purchase':
            wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_rejection_other_expense_1')

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
    
    def _send_wa_approval_other_income_expense(self, approver, phone_num, created_date, submitter):
        if self.voucher_type == 'sale':
            wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_approval_other_income_1')
        elif self.voucher_type == 'purchase':
            wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_approval_other_expense_1')
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

    def _send_wa_request_for_approval_other_income_expense(self, approver, phone_num, currency, url, submitter):
            if self.voucher_type == 'sale':
                wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_request_approval_other_income_1')
            elif self.voucher_type == 'purchase':
                wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_request_approval_other_expense_1')
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
        
    def send_request_for_approval(self):
        for record in self:
            if record.voucher_type == 'sale':
                action_id = self.env.ref('aos_account_voucher.action_receipt_voucher_list_aos_voucher')
                template_id = self.env.ref('equip3_accounting_operation.email_template_other_income_approval_matrix')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_request_for_other_income')
            elif record.voucher_type == 'purchase':
                action_id = self.env.ref('aos_account_voucher.action_review_voucher_list_aos_voucher')
                template_id = self.env.ref('equip3_accounting_operation.email_template_other_expense_approval_matrix')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_request_for_other_expense')
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
            url = base_url + '/web#id=' + \
                str(record.id) + '&action=' + str(action_id.id) + \
                '&view_type=form&model=account.voucher'
            currency = record.currency_id.symbol + str(record.amount)
            invoice_name = 'Draft Other Income' if record.state != 'posted' else record.name
            record.request_partner_id = self.env.user.partner_id.id
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
                        "payment_journal" : record.payment_journal_id.name,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    phone_num = str(approver.mobile or approver.partner_id.mobile)
                    if self.is_allowed_to_wa_notification:
                        record._send_wa_request_for_approval_other_income_expense(approver, phone_num, currency, url, submitter=self.env.user.name)
              
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
                    "payment_journal" : record.payment_journal_id.name,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                phone_num = str(approver.mobile or approver.partner_id.mobile)
                if self.is_allowed_to_wa_notification:
                    record._send_wa_request_for_approval_other_income_expense(approver, phone_num, currency, url, submitter=self.env.user.name)
               
            record.write({'state': 'to_approve'})

    def action_approve(self):
        for record in self:
            if record.voucher_type == 'sale':
                action_id = self.env.ref('aos_account_voucher.action_receipt_voucher_list_aos_voucher')
                template_id_submitter = self.env.ref('equip3_accounting_operation.email_template_other_income_submitter_approval_matrix')
                wa_template_submitted = self.env.ref('equip3_accounting_operation.wa_template_approval_other_income')
            elif record.voucher_type == 'purchase':
                action_id = self.env.ref('aos_account_voucher.action_review_voucher_list_aos_voucher')
                template_id_submitter = self.env.ref('equip3_accounting_operation.email_template_other_expense_submitter_approval_matrix')
                wa_template_submitted = self.env.ref('equip3_accounting_operation.wa_template_approval_other_expense')
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
                # record.proforma_voucher()
                record.action_move_line_create()
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
                    "date_invoice": record.account_date,
                    "currency": currency,
                }
                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                phone_num = str(record.request_partner_id.mobile)
                if record.is_allowed_to_wa_notification:
                    record._send_wa_approval_other_income_expense(record.request_partner_id, phone_num, record.create_date.date(), self.env.user.name)
                
                
    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Voucher Marix Reject ',
            'res_model': 'voucher.matrix.reject',
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
                submitter_name = record.request_partner_id.name or ''  # Fallback to empty string if None
                string_test = string_test.replace("${submitter_name}", str(submitter_name))
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

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        return

    @api.onchange('partner_id')
    def branch_domain(self):
        res = {}
        self._get_approve_button_from_config()
        if self.user_id and self.user_id.branch_ids:
            res = {
                'domain': {
                    'branch_id': [('id', 'in', self.env.branches.ids),('company_id','=', self.env.company.id)]
                }
            }
        return res

    @api.depends('tax_correction', 'line_ids.price_subtotal')
    def _compute_total(self):
        tax_calculation_rounding_method = self.env.user.company_id.tax_calculation_rounding_method
        for voucher in self:
            total = 0
            tax_amount = 0
            tax_lines_vals_merged = {}
            for line in voucher.line_ids:
                tax_info = line.tax_ids.compute_all(line.price_unit, voucher.currency_id, line.quantity,
                                                    line.product_id, voucher.partner_id)
                if tax_calculation_rounding_method == 'round_globally':
                    total += tax_info.get('total_excluded', 0.0)
                    for t in tax_info.get('taxes', False):
                        key = (
                            t['id'],
                            t['account_id'],
                        )
                        if key not in tax_lines_vals_merged:
                            tax_lines_vals_merged[key] = t.get('amount', 0.0)
                        else:
                            tax_lines_vals_merged[key] += t.get('amount', 0.0)
                else:
                    total += tax_info.get('total_included', 0.0)
                    tax_amount += sum([t.get('amount', 0.0)
                                      for t in tax_info.get('taxes', False)])
            if tax_calculation_rounding_method == 'round_globally':
                tax_amount = sum([voucher.currency_id.round(t)
                                 for t in tax_lines_vals_merged.values()])
                voucher.amount = total + tax_amount + voucher.tax_correction
            else:
                voucher.amount = total + voucher.tax_correction
            voucher.tax_amount = tax_amount
            voucher.untax_amount = voucher.amount - tax_amount

    def _get_journal_currency(self):
        self.currency_id = self.currency_id.id

    def voucher_move_line_create(self, line_total, move_id, company_currency, current_currency):
        for line in self.line_ids:
            if not line.price_subtotal:
                continue
            tax_amount = 0
            amount = self._convert(line.price_unit * line.quantity)
            if (line.tax_ids):
                tax_group = line.tax_ids.compute_all(line.price_unit, line.currency_id, line.quantity, line.product_id, self.partner_id)
                # if move_line['debit']: move_line['debit'] = tax_group['total_excluded']
                # if move_line['credit']: move_line['credit'] = tax_group['total_excluded']
                for tax_vals in tax_group['taxes']:
                    if tax_vals['amount']:
                        tax_amount = tax_vals['amount']
                        tax = self.env['account.tax'].browse([tax_vals['id']])
                        # account_id = (tax.account_id and tax.account_id.id or False)
                        if self.voucher_type == 'purchase':
                            if tax_amount < 0.0:
                                debit = 0.0
                                credit = abs(tax_amount)
                            else:
                                debit = abs(tax_amount)
                                credit = 0.0
                        else:
                            if tax_amount > 0.0:
                                debit = 0.0
                                credit = abs(tax_amount)
                            else:
                                debit = abs(tax_amount)
                                credit = 0.0
                        account_id = (amount > 0 and tax_vals['account_id'])
                        if not account_id:
                            account_id = line.account_id.id
                        temp = {
                            'account_id': account_id,
                            'name': line.name + ' ' + tax_vals['name'],
                            'tax_line_id': tax_vals['id'],
                            'move_id': move_id,
                            'date': self.account_date,
                            'partner_id': self.partner_id.id,
                            # 'debit': self.voucher_type != 'sale' and abs(debit) or 0.0,
                            # 'credit': self.voucher_type == 'sale' and abs(credit) or 0.0,
                            'credit': abs(credit) if credit > 0.0 else 0.0,
                            'debit': abs(debit) if debit > 0.0 else 0.0,
                            'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)] or False,
                        }
                        if company_currency != current_currency:
                            ctx = {}
                            if self.account_date:
                                ctx['date'] = self.account_date
                            temp['currency_id'] = current_currency
                            # amount_debit_credit = self._convert(tax_vals['amount'], self.env.company.currency_id, line.company_id, self.account_date or fields.Date.today(), round=True)
                            # amount_debit_credit = self.currency_id._convert(tax_vals['amount'], self.env.company.currency_id, line.company_id, self.account_date or fields.Date.today(), round=True)
                            amount_debit_credit = self._convert(
                                tax_vals['amount'])
                            amount_curr = tax_vals['amount']
                            if temp['debit'] == 0:
                                if amount_curr > 0:
                                    amount_curr = -amount_curr
                            else:
                                if amount_curr < 0:
                                    amount_curr = -amount_curr

                            temp['amount_currency'] = amount_curr
                            temp['debit'] = self.voucher_type != 'sale' and amount_debit_credit or 0.0
                            temp['credit'] = self.voucher_type == 'sale' and amount_debit_credit or 0.0
                        self.env['account.move.line'].create(temp)
            if line.price_subtotal != amount:
                amount_journal = (line.price_subtotal - tax_amount)
            else:
                amount_journal = (amount - tax_amount)
            move_line = self._prepare_voucher_move_line(line, amount_journal, move_id, company_currency, current_currency)
            self.env['account.move.line'].create(move_line)
        return line_total

    def account_move_get(self):
        move = super(AccountVoucher, self).account_move_get()
        for rec in self:
            move.update({'branch_id': rec.branch_id.id,
                         'analytic_group_ids': [(6, 0, rec.analytic_group_ids.ids)]})
        return move
class AccountVoucherLine(models.Model):
    _inherit = 'account.voucher.line'

    def _domain_account_id(self):
        domain_ids = []
        if self.env.context.get("default_voucher_type") == 'sale':
            account_expenses = self.env.ref('account.data_account_type_expenses').id
            account_other_expense = self.env.ref('equip3_accounting_masterdata.data_acc_t_other_expense').id
            domain_ids = [account_expenses, account_other_expense]
        elif self.env.context.get("default_voucher_type") == 'purchase':
            account_income = self.env.ref('account.data_account_type_revenue').id
            account_other_income = self.env.ref('account.data_account_type_other_income').id
            domain_ids = [account_income, account_other_income]

        return [('user_type_id','not in', domain_ids)]

    account_id = fields.Many2one('account.account', string='Account', required=True,
        help="The income or expense account related to the selected product.", domain=_domain_account_id)

    @api.onchange('quantity', 'price_unit', 'tax_ids')
    def _compute_subtotal(self):
        for line in self:
            line.update(line._get_price_total_and_subtotal())

    @api.onchange('product_id')
    def set_analytic_group_ids(self):
        for res in self:
            res.update(
                {'analytic_tag_ids': [(6, 0, res.voucher_id.analytic_group_ids.ids)], })

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            line.tax_ids = taxes

            line.price_unit = line._get_computed_price_unit()

    def _get_computed_name(self):
        self.ensure_one()
        if not self.product_id:
            return ''

        if self.voucher_id.partner_id.lang:
            product = self.product_id.with_context(
                lang=self.voucher_id.partner_id.lang)
            line.update(line._get_price_total_and_subtotal())

    @api.onchange('product_id', 'currency_id')
    def _onchange_product_id(self):
        for line in self:
            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            line.tax_ids = taxes

            line.price_unit = line._get_computed_price_unit()

    def _get_computed_name(self):
        self.ensure_one()
        if not self.product_id:
            return ''

        if self.voucher_id.partner_id.lang:
            product = self.product_id.with_context(
                lang=self.voucher_id.partner_id.lang)
        else:
            product = self.product_id

        values = []
        if product.partner_ref:
            values.append(product.partner_ref)
        if self.voucher_id.voucher_type == 'sale':
            if product.description_sale:
                values.append(product.description_sale)
        elif self.voucher_id.voucher_type == 'purchase':
            if product.description_purchase:
                values.append(product.description_purchase)
        return '\n'.join(values)

    def _get_computed_account(self):
        self.ensure_one()
        self = self.with_company(self.voucher_id.journal_id.company_id)

        if not self.product_id:
            return

        accounts = self.product_id.product_tmpl_id.get_product_accounts(
            fiscal_pos=None)
        if self.voucher_id.voucher_type == 'sale':
            # Out invoice.
            return accounts['income'] or self.account_id
        elif self.voucher_id.voucher_type == 'purchase':
            # In invoice.
            return accounts['expense'] or self.account_id

    def _get_computed_taxes(self):
        self.ensure_one()

        if self.voucher_id.voucher_type == 'sale':
            # Out invoice.
            if self.product_id.taxes_id:
                tax_ids = self.product_id.taxes_id.filtered(
                    lambda tax: tax.company_id == self.voucher_id.company_id)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids:
                tax_ids = self.voucher_id.company_id.account_sale_tax_id
        elif self.voucher_id.voucher_type == 'purchase':
            # In invoice.
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.filtered(
                    lambda tax: tax.company_id == self.voucher_id.company_id)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids:
                tax_ids = self.voucher_id.company_id.account_purchase_tax_id
        else:
            # Miscellaneous operation.
            tax_ids = self.account_id.tax_ids

        if self.company_id and tax_ids:
            tax_ids = tax_ids.filtered(
                lambda tax: tax.company_id == self.company_id)

        return tax_ids

    # def _get_computed_uom(self):
    #     self.ensure_one()
    #     if self.product_id:
    #         return self.product_id.uom_id
    #     return False

    def _get_computed_price_unit(self):
        self.ensure_one()

        if not self.product_id:
            return 0.0

        company = self.voucher_id.company_id
        currency = self.voucher_id.currency_id
        company_currency = company.currency_id
        product_uom = self.product_id.uom_id
        move_date = self.voucher_id.date or fields.Date.context_today(self)

        if self.voucher_id.voucher_type == 'sale':
            product_price_unit = self.product_id.lst_price
            product_taxes = self.product_id.taxes_id
        elif self.voucher_id.voucher_type == 'purchase':
            product_price_unit = self.product_id.standard_price
            product_taxes = self.product_id.supplier_taxes_id
        else:
            return 0.0
        product_taxes = product_taxes.filtered(
            lambda tax: tax.company_id == company)

        # Apply currency rate.
        if currency and currency != company_currency:
            product_price_unit = company_currency._convert(
                product_price_unit, currency, company, move_date)

        return product_price_unit

    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, currency=None, product=None, partner=None,
                                      taxes=None, move_type=None):
        self.ensure_one()
        return self._get_price_total_and_subtotal_model(
            price_unit=price_unit or self.price_unit,
            quantity=quantity or self.quantity,
            currency=currency or self.currency_id,
            product=product or self.product_id,
            partner=partner or self.voucher_id.partner_id,
            taxes=taxes or self.tax_ids,
            move_type=move_type or self.voucher_id.voucher_type,
        )

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, currency, product, partner, taxes, move_type):
        res = {}

        # Compute 'price_subtotal'.
        line_discount_price_unit = price_unit
        subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        if taxes:
            force_sign = -1 if move_type in ('sale') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit,
                                                                                      quantity=quantity,
                                                                                      currency=currency,
                                                                                      product=product, partner=partner,
                                                                                      is_refund=None)
            # res['price_subtotal'] = taxes_res['total_excluded']
            # res['price_total'] = taxes_res['total_included']
            res['price_subtotal'] = taxes_res['total_included']
            res['price_untaxed'] = taxes_res['total_excluded']
        else:
            # res['price_total'] = res['price_subtotal'] = subtotal
            res['price_subtotal'] = subtotal
            res['price_untaxed'] = subtotal
        # In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    def product_id_change(self, product_id, partner_id=False, price_unit=False, company_id=None, currency_id=None,
                          type=None):
        # TDE note: mix of old and new onchange badly written in 9, multi but does not use record set
        context = self._context
        company_id = company_id if company_id is not None else context.get(
            'company_id', False)
        company = self.env['res.company'].browse(company_id)
        currency = self.env['res.currency'].browse(currency_id)
        # if not partner_id:
        #    raise UserError(_("You must first select a partner."))
        part = self.env['res.partner'].browse(partner_id)
        if not part:
            part = company.partner_id
        if part.lang:
            self = self.with_context(lang=part.lang)

        product = self.env['product.product'].browse(product_id)
        fpos = part.property_account_position_id
        account = self._get_account(product, fpos, type)
        values = {
            'name': product.partner_ref,
        }

        if not self.account_id:
            values['account_id'] = account.id

        if type == 'purchase':
            values['price_unit'] = price_unit or product.standard_price
            taxes = product.supplier_taxes_id or account.tax_ids
            if product.description_purchase:
                values['name'] += '\n' + product.description_purchase
        else:
            values['price_unit'] = price_unit or product.lst_price
            taxes = product.taxes_id or account.tax_ids
            if product.description_sale:
                values['name'] += '\n' + product.description_sale

        values['tax_ids'] = taxes.ids
        values['uom_id'] = product.uom_id.id
        if company and currency:
            if company.currency_id != currency:
                if type == 'purchase':
                    values['price_unit'] = price_unit or product.standard_price
                values['price_unit'] = values['price_unit']

        return {'value': values, 'domain': {}}


class ApprovalMatrixAccountingLines(models.Model):
    _inherit = "approval.matrix.accounting.lines"

    voucher_id = fields.Many2one('account.voucher', string='Voucher')
