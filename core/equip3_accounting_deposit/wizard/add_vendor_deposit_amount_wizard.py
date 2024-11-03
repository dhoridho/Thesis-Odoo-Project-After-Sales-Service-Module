# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, date, timedelta
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError

class VendorDepositAmountWizard(models.TransientModel):
    _name = 'vendor.deposit.amount.wizard'
    _description = 'vendor deposit amount wizard'

    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    deposit_amount = fields.Monetary(currency_field='currency_id', string='Deposit Amount')
    final_amount = fields.Monetary(currency_field='currency_id', string='Final Amount', compute='_compute_amount_adding_deposit', readonly=True)
    final_remaining_amount = fields.Monetary(currency_field='currency_id', string='Final Remaining Amount', compute='_compute_amount_adding_deposit', readonly=True)
    is_vendor_deposit_approval_matrix = fields.Boolean(string="Is Vendor Deposite Approval Matrix")
    approve_vendor_deposit = fields.Boolean(string="Approva Vendor Deposite")
    date = fields.Date(string='Date', default=fields.Date.context_today)
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get('active_model') == 'vendor.deposit':
            vendor_deposit_id = self.env['vendor.deposit'].browse([self._context.get('active_id')])
        else:
            raise UserError(_(
                "The add amount Vendor deposit wizard should only be called on vendor.deposit records."
            ))
        if vendor_deposit_id.state != 'post':
            raise UserError(_("You can only add amount deposit for paid deposit only."))

        res['currency_id'] = vendor_deposit_id.currency_id.id
        res['is_vendor_deposit_approval_matrix'] = vendor_deposit_id.is_vendor_deposit_approval_matrix
        res['approve_vendor_deposit'] = vendor_deposit_id.approve_add_amount
        if vendor_deposit_id.add_amount_approver != 0:
            res['deposit_amount'] = vendor_deposit_id.add_amount_approver
        return res
    
    @api.depends('deposit_amount')
    def _compute_amount_adding_deposit(self):
        vendor_deposit_id = self.env['vendor.deposit'].browse([self._context.get('active_id')])
        current_amount = vendor_deposit_id.amount
        current_remaining_amount = vendor_deposit_id.remaining_amount
        amount = 0 or self.deposit_amount
        self.final_amount = (amount + current_amount)
        self.final_remaining_amount = (amount + current_remaining_amount)

    def action_request_for_approval(self):
        if self.deposit_amount <= 0:
            raise ValidationError("Deposit amount must be greater than 0.")
        vendor_deposit_id = self.env['vendor.deposit'].browse([self._context.get('active_id')])
        for record in vendor_deposit_id:
            action_id = self.env.ref('equip3_accounting_deposit.action_vendor_deposit')
            template_id = self.env.ref('equip3_accounting_deposit.email_template_vendor_deposit_approval_matrix')
            wa_template_id = self.env.ref('equip3_accounting_deposit.wa_template_vendor_deposit_approval_matrix')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=vendor.deposit'
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
                        "due_date": record.payment_date,
                        "currency": currency,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    phone_num = approver.partner_id.mobile
                    if record.is_allowed_to_wa_notification_vendor_deposit:
                        record._send_wa_request_for_approval_vendor_deposit(approver, phone_num, currency, url, submitter=self.env.user.name)
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
                    "due_date": record.payment_date,
                    "currency": currency,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                phone_num = approver.partner_id.mobile
                if record.is_allowed_to_wa_notification_vendor_deposit:
                    record._send_wa_request_for_approval_vendor_deposit(approver, phone_num, currency, url, submitter=self.env.user.name)
                # record._send_whatsapp_message(wa_template_id, approver, currency, url)
            # record.write({'deposit_count': record.deposit_count+1})
            vals = {
                'vendor_deposit_id': record.id,
                'date': self.date,
                'amount': self.deposit_amount,
            }
            move_id = self.env['vendor.deposit.approval.line'].create(vals)
            record.write({'deposit_count': record.deposit_count+1})

    def action_approve(self):
        vendor_deposit_id = self.env['vendor.deposit'].browse([self._context.get('active_id')])
        for record in vendor_deposit_id:
            action_id = self.env.ref('equip3_accounting_deposit.action_vendor_deposit')
            template_id = self.env.ref('equip3_accounting_deposit.email_template_vendor_deposit_approval_matrix')
            template_id_submitter = self.env.ref('equip3_accounting_deposit.email_template_vendor_deposit_submitter_approval_matrix')
            wa_template_id = self.env.ref('equip3_accounting_deposit.wa_template_vendor_deposit_approval_matrix')
            wa_template_id_submitter = self.env.ref('equip3_accounting_deposit.wa_template_vendor_deposit_submitter_approval_matrix')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=vendor.deposit'
            created_date = record.create_date.date()
            user = self.env.user
            currency = ''
            if record.currency_id.position == 'before':
               currency = record.currency_id.symbol + str(record.amount)
            else:
                currency = str(record.amount) + ' ' + record.currency_id.symbol
            user = self.env.user
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
                                    "due_date": record.payment_date,
                                    "currency": currency,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if record.is_allowed_to_wa_notification_vendor_deposit:
                                    record._send_wa_approval_vendor_deposit(approving_matrix_line_user, approving_matrix_line_user.mobile, created_date, self.env.user.name)
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
                                    "due_date": record.payment_date,
                                    "currency": currency,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if record.is_allowed_to_wa_notification_vendor_deposit:
                                    record._send_wa_approval_vendor_deposit(next_approval_matrix_line_id[0].user_ids[0], next_approval_matrix_line_id[0].user_ids[0].mobile, created_date, self.env.user.name)
                                # record._send_whatsapp_message(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], currency, url)
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                self.action_confirm()
                record.write({'add_amount_approver': 0, 'approve_add_amount': False, 'deposit_count': record.deposit_count-1})
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.request_partner_id.email,
                    'approver_name' : record.name,
                    'date': date.today(),
                    'create_date': record.create_date.date(),
                    'submitter' : self.env.user.name,
                    'url' : url,
                    "due_date": record.payment_date,
                    "currency": currency,
                }
                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                if record.is_allowed_to_wa_notification_vendor_deposit:
                    record._send_wa_approval_vendor_deposit(record.request_partner_id, record.request_partner_id.mobile, created_date, self.env.user.name)
                # record._send_whatsapp_message(wa_template_id_submitter, record.request_partner_id.user_ids, currency, url)

    def action_reject(self):
        vendor_deposit_id = self.env['vendor.deposit'].browse([self._context.get('active_id')])
        context = dict(self.env.context) or {}
        context.update({'default_add_amount': True, 'active_model': 'vendor.deposit','active_ids': vendor_deposit_id.ids})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Deposit ',
            'res_model': 'wizard.vendor.deposit',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def action_confirm(self):
        for record in self:
            vendor_deposit_id = self.env['vendor.deposit'].browse([self._context.get('active_id')])
            debit_vals = {
                'partner_id': vendor_deposit_id.partner_id.id,
                'name': vendor_deposit_id.journal_id.payment_debit_account_id.name,
                'date': date.today(),
                'analytic_tag_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
                'currency_id': record.currency_id.id,
                'account_id': vendor_deposit_id.deposit_account_id.id,
                'debit': abs(record.deposit_amount),
                'credit': 0.0,
            }
            credit_vals = {
                'partner_id': vendor_deposit_id.partner_id.id,
                'name': vendor_deposit_id.deposit_account_id.name,
                'date': date.today(),
                'analytic_tag_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
                'currency_id': record.currency_id.id,
                'account_id': vendor_deposit_id.journal_id.payment_credit_account_id.id,
                'debit': 0.0,
                'credit': abs(record.deposit_amount),
            }
            vals = {
                'ref': 'Add Amount Vendor Deposit ' + vendor_deposit_id.name,
                'partner_id': vendor_deposit_id.partner_id.id,
                'currency_id': record.currency_id.id,
                'date': date.today(),
                'journal_id': vendor_deposit_id.journal_id.id,
                'branch_id': vendor_deposit_id.branch_id.id,
                'analytic_group_ids': [(6, 0, vendor_deposit_id.analytic_group_ids.ids)],
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move_id = self.env['account.move'].create(vals)
            move_id.post()
            vendor_deposit_id.deposit_history += move_id
            

