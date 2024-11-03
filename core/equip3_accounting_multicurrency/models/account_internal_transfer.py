from odoo import tools, api, fields, models, _
from datetime import date, datetime
from lxml import etree
import pytz
from pytz import timezone, UTC
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, ValidationError
from ...equip3_general_features.models.email_wa_parameter import waParam

from lxml import etree
import logging
import requests, json
import base64

_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json'}


class AccountInternalTransfer(models.Model):
    _inherit = "account.internal.transfer"


    # def _send_whatsapp_message(self, template_id, approver, currency=False, url=False, reason=False):
    #     for record in self:
    #         string_test = str(tools.html2plaintext(template_id.body_html))
    #         if "${approver_name}" in string_test:
    #             string_test = string_test.replace("${approver_name}", approver.name)
    #         if "${submitter_name}" in string_test:
    #             string_test = string_test.replace("${submitter_name}", record.request_partner_id.name)
    #         if "${amount}" in string_test:
    #             string_test = string_test.replace("${amount}", str(record.amount))
    #         if "${currency}" in string_test:
    #             string_test = string_test.replace("${currency}", currency)
    #         if "${bank_from}" in string_test:
    #             string_test = string_test.replace("${bank_from}", record.bank_from_journal_id.name)
    #         if "${bank_to}" in string_test:
    #             string_test = string_test.replace("${bank_to}", record.bank_to_journal_id.name)
    #         if "${transfer_date}" in string_test:
    #             string_test = string_test.replace("${transfer_date}", fields.Datetime.from_string(
    #                 record.transfer_date).strftime('%d/%m/%Y'))
    #         if "${create_date}" in string_test:
    #             string_test = string_test.replace("${create_date}", fields.Datetime.from_string(
    #                 record.create_date).strftime('%d/%m/%Y'))
    #         if "${feedback}" in string_test:
    #             string_test = string_test.replace("${feedback}", reason)
    #         if "${br}" in string_test:
    #             string_test = string_test.replace("${br}", f"\n")
    #         if "${url}" in string_test:
    #             string_test = string_test.replace("${url}", url)
    #         phone_num = str(approver.mobile or approver.employee_phone)
    #         if "+" in phone_num:
    #             phone_num = phone_num.replace("+", "")
    #         param = {'body': string_test, 'text': string_test, 'phone': phone_num, 'previewBase64': '', 'title': ''}
    #         domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
    #         token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
    #         try:
    #             request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
    #         except ConnectionError:
    #             raise ValidationError("Not connect to API Chat Server. Limit reached or not active")
    
    @api.model
    def _send_wa_message_purchase_currency(self, template_id, approver, currency=False, url=False, reason=False):
        wa_sender = waParam()
        for record in self:
            if not template_id.broadcast_template_id:
                raise ValidationError(_("Broadcast Template must be set first in Whatsapp Template!"))
            string_test = str(template_id.message)
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${rejecter_user}" in string_test:
                string_test = string_test.replace("${rejecter_user}", approver.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", record.request_partner_id.name)
            if "${amount_currency}" in string_test:
                string_test = string_test.replace("${amount_currency}", currency)
            if "${date_purchase_currency}" in string_test:
                string_test = string_test.replace("${date_purchase_currency}", fields.Datetime.from_string(record.transfer_date).strftime('%d/%m/%Y'))
            if "${create_date}" in string_test:
                string_test = string_test.replace("${create_date}", fields.Datetime.from_string(record.create_date).strftime('%d/%m/%Y'))
            if "${feedback}" in string_test:
                string_test = string_test.replace("${feedback}", reason)
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            phone_num = str(approver.mobile or approver.phone)
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "")
            wa_sender.set_wa_string(string_test, template_id._name, template_id=template_id)
            wa_sender.send_wa(phone_num)




    # administration = fields.Boolean(string='Administration', default=False, tracking=True)
    # # show when administration = true – mandatory
    # administration_account = fields.Many2one('account.account', string="Administration Account", tracking=True)
    # administration_fee = fields.Monetary(string="Amount", currency_field='currency_id', tracking=True)
    # state = fields.Selection(selection=[
    #         ('draft', 'Draft'),
    #         ('in_progress', 'In Progress'),
    #         ('done', 'Completed'),
    #     ], string='State', default='draft', tracking=True)
    
    apply_manual_currency_exchange = fields.Boolean(string="Apply Manual Currency Exchange")
    manual_currency_exchange_rate = fields.Float(string="Manual Currency Exchange Rate", digits=(12,12))
    manual_currency_exchange_inverse_rate = fields.Float(string="Inverse Rate")

    type_curr = fields.Selection(selection=[
            ('bank_cash', 'Internal Transfer'),
            ('purchase_currency', 'Purchase Currency'),
        ], string='Type', default="bank_cash")

    # @api.depends('manual_currency_exchange_inverse_rate')
    # def _calculate_exchange_rate(self):
    #     for rec in self:
    #         if rec.manual_currency_exchange_inverse_rate > 0:
    #             rec.manual_currency_exchange_rate = 1/rec.manual_currency_exchange_inverse_rate


    def action_request_for_approval(self):
        for record in self:
            if record.type_curr == "purchase_currency":
                action_id = self.env.ref('equip3_accounting_multicurrency.action_int_trans_pur_currency')
                template_id = self.env.ref('equip3_accounting_multicurrency.email_template_purchase_currency_approval_matrix')
                wa_template_id = self.env.ref('equip3_accounting_multicurrency.wa_template_purchase_currency_approval')
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.internal.transfer'
                currency = ''
                if record.currency_id.position == 'before':
                    currency = record.currency_id.symbol + str(record.transfer_amount)
                else:
                    currency = str(record.transfer_amount) + ' ' + record.currency_id.symbol
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
                            "due_date": record.transfer_date,
                            "date_invoice": record.create_date.date(),
                            "currency": currency,
                        }
                        template_id.with_context(ctx).send_mail(record.id, True)
                        record._send_wa_message_purchase_currency(wa_template_id, approver, currency, url)
                else:
                    approver = record.approved_matrix_ids[0].user_ids[0]
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.partner_id.email,
                        'approver_name' : approver.name,
                        'date': date.today(),
                        'submitter' : self.env.user.name,
                        'url' : url,
                        "due_date": record.transfer_date,
                        "date_invoice": record.create_date.date(),
                        "currency": currency,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    record._send_wa_message_purchase_currency(wa_template_id, approver, currency, url)
                record.write({'state': 'to_approve'})
            else:
                return super(AccountInternalTransfer, self).action_request_for_approval()
    
    def action_approve(self):
        for record in self:
            if record.type_curr == "purchase_currency":
                action_id = self.env.ref('equip3_accounting_multicurrency.action_int_trans_pur_currency')
                template_id = self.env.ref('equip3_accounting_multicurrency.email_template_purchase_currency_approval_matrix')
                template_id_submitter = self.env.ref('equip3_accounting_multicurrency.email_template_purchase_currency_approval_submitter_matrix')
                wa_template_id = self.env.ref('equip3_accounting_multicurrency.wa_template_purchase_currency_approval')
                wa_template_id_submitter = self.env.ref('equip3_accounting_multicurrency.wa_template_purchase_currency_approved')
                user = self.env.user
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.internal.transfer'
                currency = ''
                if record.currency_id.position == 'before':
                    currency = record.currency_id.symbol + str(record.transfer_amount)
                else:
                    currency = str(record.transfer_amount) + ' ' + record.currency_id.symbol
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
                                        "due_date": record.transfer_date,
                                        "date_invoice": record.create_date.date(),
                                        "currency": currency,
                                    }
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                    record._send_wa_message_purchase_currency(wa_template_id, approving_matrix_line_user, currency, url)
                            else:
                                if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                    ctx = {
                                        'email_from' : self.env.user.company_id.email,
                                        'email_to' : next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                        'approver_name' : next_approval_matrix_line_id[0].user_ids[0].name,
                                        'date': date.today(),
                                        'submitter' : self.env.user.name,
                                        'url' : url,
                                        "due_date": record.transfer_date,
                                        "date_invoice":record.create_date.date(),
                                        "currency": currency,
                                    }
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                    record._send_wa_message_purchase_currency(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], currency, url)
                if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r:r.approved)):
                    record.write({'state': 'approved'})
                    record.action_validate()
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : record.request_partner_id.email,
                        'approver_name' : record.name,
                        'date': date.today(),
                        'create_date': record.create_date.date(),
                        'submitter' : self.env.user.name,
                        'url' : url,
                        "due_date": record.transfer_date,
                        "currency": currency,
                    }
                    template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                    record._send_wa_message_purchase_currency(wa_template_id_submitter, record.request_partner_id.user_ids, currency, url)
            else:
                return super(AccountInternalTransfer, self).action_approve()

    def action_reject(self):
        res = super(AccountInternalTransfer, self).action_reject()
        if self.type_curr == "purchase_currency":
            res['name'] = "Purchase Currency Matrix Reject"
        return res

    @api.onchange('manual_currency_exchange_inverse_rate')
    def _oncange_rate_conversion(self):
        if self.manual_currency_exchange_inverse_rate:
            self.manual_currency_exchange_rate = 1 / self.manual_currency_exchange_inverse_rate

    @api.onchange('manual_currency_exchange_rate')
    def _oncange_rate(self):
        if self.manual_currency_exchange_rate:
            self.manual_currency_exchange_inverse_rate = 1 / self.manual_currency_exchange_rate

    @api.depends('transfer_amount', 'company_id', 'branch_id')
    def _get_approval_matrix(self):
        for record in self:
            matrix_id = False
            if record.type_curr == "bank_cash":
                matrix_id = self.env['approval.matrix.accounting'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('min_amount', '<=', record.transfer_amount),
                        ('max_amount', '>=', record.transfer_amount),
                        ('approval_matrix_type', '=', 'inter_bank_cash_approval_matrix')
                    ], limit=1)
            elif record.type_curr == "purchase_currency":
                matrix_id = self.env['approval.matrix.accounting'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('min_amount', '<=', record.transfer_amount),
                        ('max_amount', '>=', record.transfer_amount),
                        ('approval_matrix_type', '=', 'purchase_currency_approval_matrix')
                    ], limit=1)
            record.approval_matrix_id = matrix_id
            record._compute_approving_matrix_lines()

    def _get_approve_button_from_config(self):
        for record in self:
            is_internal_approval_matrix = False
            if record.type_curr == 'bank_cash':
                is_internal_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_internal_transfer_approval_matrix', False)
            elif record.type_curr == 'purchase_currency':
                is_internal_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_purchase_currency_approval_matrix', False)
            record.is_internal_approval_matrix = is_internal_approval_matrix
    
    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'transfer_date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['transfer_date']))
            
            if self._context.get('default_type_curr') == 'bank_cash':
                vals['name'] = self.env['ir.sequence'].next_by_code('account.internal.transfer', sequence_date=seq_date) or _('New')
            elif self._context.get('default_type_curr') == 'purchase_currency':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.currency', sequence_date=seq_date) or _('New')
        result = super(AccountInternalTransfer, self).create(vals)
        return result

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(AccountInternalTransfer, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(result['arch'])
            type_curr = self._context.get('default_type_curr')
            if type_curr == "purchase_currency":
                bank_from_journal_id = doc.xpath("//field[@name='bank_from_journal_id']")
                bank_from_journal_id[0].set("string", "Sold Currency")
                bank_to_journal_id = doc.xpath("//field[@name='bank_to_journal_id']")
                bank_to_journal_id[0].set("string", "Purchased Currency")
                result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

    # @api.onchange('bank_to_journal_id')
    # def currency(self):
    #     for rec in self:
    #         if rec.bank_to_journal_id:
    #             rec.currency_id = rec.bank_to_journal_id.currency_id


    def warning_message(self,value):
        if value <= 0:
            raise UserError(_("Purchase amount should bigger than 0!"))

    def action_validate(self):
        res =super(AccountInternalTransfer, self).action_validate()
        for record in self:
            self.warning_message(abs(record.transfer_amount))
            ref = ''
            name = ''
            if record.type_curr == 'bank_cash':
                ref = 'Internal Transfer' + ' ' + (record.transfer_desc or '')
                name = 'Internal Transfer' +' ' + (record.name or '')
            elif record.type_curr == 'purchase_currency':
                ref = 'Purchase Currency' + ' ' + (record.transfer_desc or '')
                name = 'Purchase Currency' +' ' + (record.name or '')

            counterpart_transfer_amount = abs(record.transfer_amount)
            counterpart_administration_fee = abs(record.administration_fee)
            counterpart_amount = counterpart_transfer_amount + counterpart_administration_fee
            company_currency = record.company_id.currency_id

            # Manage currency.
            if record.currency_id == company_currency:
                # Single-currency.
                balance_transfer_amount = counterpart_transfer_amount
                balance_administration_fee = counterpart_administration_fee
                balance = counterpart_amount
                counterpart_transfer_amount = 0.0
                counterpart_administration_fee = 0.0
                counterpart_amount = 0.0
                currency_id = False
            else:
                # Multi-currencies.
                if record.apply_manual_currency_exchange == True:
                    balance_transfer_amount = counterpart_transfer_amount/record.manual_currency_exchange_rate
                    balance_administration_fee = counterpart_administration_fee/record.manual_currency_exchange_rate
                    balance = balance_transfer_amount + balance_administration_fee
                else:
                    balance_transfer_amount = record.currency_id._convert(counterpart_transfer_amount, company_currency, record.company_id, record.transfer_date)
                    balance_administration_fee = record.currency_id._convert(counterpart_administration_fee, company_currency, record.company_id, record.transfer_date)
                    balance = record.currency_id._convert(counterpart_amount, company_currency, record.company_id, record.transfer_date)

                currency_id = record.currency_id.id

            move_ids = self.env['account.move'].search([('internal_tf_id', '=', record.id)])
            
            if not move_ids and record.transfer_in_transit == True and record.administration == True:                
                credit_vals = {
                        'name': name,
                        'amount_currency': -counterpart_amount,
                        'currency_id': currency_id,
                        'debit': 0.0,
                        'credit': abs(balance),
                        'date_maturity': record.transfer_date,
                        'account_id': record.bank_from_journal_id.payment_credit_account_id.id,
                    }

                debit_vals1 = {
                        'name': name,
                        'amount_currency': counterpart_transfer_amount,
                        'currency_id': currency_id,
                        'debit': abs(balance_transfer_amount),
                        'credit': 0.0,
                        'date_maturity': record.transfer_date,
                        'account_id': record.account_in_transit.id,
                    }

                debit_vals2 = {
                        'name': name,
                        'amount_currency': counterpart_administration_fee,
                        'currency_id': currency_id,
                        'debit': abs(balance_administration_fee),
                        'credit': 0.0,
                        'date_maturity': record.transfer_date,
                        'account_id': record.administration_account.id,
                    }
                vals = {
                    'ref': ref,
                    'date': record.transfer_date,
                    'journal_id': record.bank_from_journal_id.id,
                    'line_ids': [(0, 0, credit_vals),(0, 0, debit_vals1),(0, 0, debit_vals2)]
                }
                
                move_id = self.env['account.move'].create(vals)
                move_id.post()
                record.write({'state': 'in_progress'})

            elif not move_ids and record.transfer_in_transit == True and record.administration == False:
                credit_vals = {
                        'name': name,
                        'amount_currency': -counterpart_transfer_amount,
                        'currency_id': currency_id,
                        'debit': 0.0,
                        'credit': abs(balance_transfer_amount),
                        'date_maturity': record.transfer_date,
                        'account_id': record.bank_from_journal_id.payment_credit_account_id.id,
                    }

                debit_vals1 = {
                        'name': name,
                        'amount_currency': counterpart_transfer_amount,
                        'currency_id': currency_id,
                        'debit': abs(balance_transfer_amount),
                        'credit': 0.0,
                        'date_maturity': record.transfer_date,
                        'account_id': record.account_in_transit.id,
                    }
                vals = {
                    'ref': ref,
                    'date': record.transfer_date,
                    'journal_id': record.bank_from_journal_id.id,
                    'line_ids': [(0, 0, credit_vals),(0, 0, debit_vals1)]
                }

                move_id = self.env['account.move'].create(vals)
                move_id.post()
                record.write({'state': 'in_progress'})

            elif not move_ids and record.transfer_in_transit == False and record.administration == True:
                credit_vals = {
                        'name': name,
                        'amount_currency': -counterpart_amount,
                        'currency_id': currency_id,
                        'debit': 0.0,
                        'credit': abs(balance),
                        'date_maturity': record.transfer_date,
                        'account_id': record.bank_from_journal_id.payment_credit_account_id.id,
                    }

                debit_vals1 = {
                        'name': name,
                        'amount_currency': counterpart_transfer_amount,
                        'currency_id': currency_id,
                        'debit': abs(balance_transfer_amount),
                        'credit': 0.0,
                        'date_maturity': record.transfer_date,
                        'account_id': record.bank_to_journal_id.payment_debit_account_id.id,
                    }

                debit_vals2 = {
                        'name': name,
                        'amount_currency': counterpart_administration_fee,
                        'currency_id': currency_id,
                        'debit': abs(balance_administration_fee),
                        'credit': 0.0,
                        'date_maturity': record.transfer_date,
                        'account_id': record.administration_account.id,
                    }
                vals = {
                    'ref': ref,
                    'date': record.transfer_date,
                    'journal_id': record.bank_from_journal_id.id,
                    'line_ids': [(0, 0, credit_vals),(0, 0, debit_vals1),(0, 0, debit_vals2)]
                }

                move_id = self.env['account.move'].create(vals)
                move_id.post()
                record.write({'state': 'done'})

            else:
                if not move_ids:
                    credit_vals = {
                            'name': name,
                            'amount_currency': -counterpart_transfer_amount,
                            'currency_id': currency_id,
                            'debit': 0.0,
                            'credit': abs(balance_transfer_amount),
                            'date_maturity': record.transfer_date,
                            'account_id': record.bank_from_journal_id.payment_credit_account_id.id,
                        }
                    debit_vals = {
                            'name': name,
                            'amount_currency': counterpart_transfer_amount,
                            'currency_id': currency_id,
                            'debit': abs(balance_transfer_amount),
                            'credit': 0.0,
                            'date_maturity': record.transfer_date,
                            'account_id': record.bank_to_journal_id.payment_debit_account_id.id,
                        }
                    vals = {
                        'ref': ref,
                        'date': record.transfer_date,
                        'journal_id': record.bank_from_journal_id.id,
                        'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
                    }

                    move_id = self.env['account.move'].create(vals)
                    move_id.post()
                    record.write({'state': 'done'})
        return res

    def action_complete(self):
        for record in self:
            if record.type_curr == 'bank_cash':
                ref = 'Internal Transfer' + ' ' + (record.transfer_desc or '')
                name = 'Internal Transfer' +' ' + (record.name or '')
            elif record.type_curr == 'purchase_currency':
                ref = 'Purchase Currency' + ' ' + (record.transfer_desc or '')
                name = 'Purchase Currency' +' ' + (record.name or '')

            # Manage currency.
            counterpart_transfer_amount = abs(record.transfer_amount)
            company_currency = record.company_id.currency_id            
            
            if record.currency_id == company_currency:
                # Single-currency.
                balance_transfer_amount = counterpart_transfer_amount
                counterpart_transfer_amount = 0.0
                currency_id = False
            else:
                # Multi-currencies.
                if record.apply_manual_currency_exchange == True:
                    balance_transfer_amount = counterpart_transfer_amount/record.manual_currency_exchange_rate
                else:
                    balance_transfer_amount = record.currency_id._convert(counterpart_transfer_amount, company_currency, record.company_id, record.transfer_date)
                currency_id = record.currency_id.id

            credit_vals = {
                    'name': name,
                    'amount_currency': -counterpart_transfer_amount,
                    'currency_id': currency_id,
                    'debit': 0.0,
                    'credit': abs(balance_transfer_amount),
                    'date_maturity': date.today(),
                    'account_id': record.account_in_transit.id
                }

            debit_vals = {
                    'name': name,
                    'amount_currency': counterpart_transfer_amount,
                    'currency_id': currency_id,
                    'debit': abs(balance_transfer_amount),
                    'credit': 0.0,
                    'date_maturity': date.today(),
                    'account_id': record.bank_to_journal_id.payment_debit_account_id.id,
                }
            vals = {
                'ref': ref,
                'date': date.today(),
                'journal_id': record.bank_to_journal_id.id,
                'line_ids': [(0, 0, credit_vals),(0, 0, debit_vals)]
            }

            move_id = self.env['account.move'].create(vals)
            move_id.post()
            record.write({'state': 'done', 'has_reconciled_entries' : True})

            domain = [('account_id', '=', self.account_in_transit.id), ('reconciled', '=', False), ('name', 'like', '%' + name)]                    
            bank_to_reconcile = move_id.line_ids.filtered_domain(domain)
            move_to_reconcile = self.env['account.move.line'].search(domain)
            for account in move_to_reconcile.account_id:
                (move_to_reconcile + bank_to_reconcile)\
                    .filtered_domain([('account_id', '=', self.account_in_transit.id), ('reconciled', '=', False), ('name', 'like', '%' + name)])\
                    .reconcile()

    def _reconciled_lines(self):
        ids = []        
        if self.type_curr == 'bank_cash':
            name = 'Internal Transfer' +' ' + self.name
        elif self.type_curr == 'purchase_currency':
            name = 'Purchase Currency' +' ' + self.name

        domain = [('account_id', '=', self.account_in_transit.id), ('name', 'like', '%' + name), ('reconciled', '=', True)]
        move_to_reconcile = self.env['account.move.line'].search(domain)
        for aml in move_to_reconcile:
            ids.extend([r.debit_move_id.id for r in aml.matched_debit_ids] if aml.credit > 0 else [r.credit_move_id.id for r in aml.matched_credit_ids])
            ids.append(aml.id)
        return ids