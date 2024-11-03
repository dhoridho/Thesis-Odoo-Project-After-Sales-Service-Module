
from odoo import api, fields, models, tools, exceptions, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
from ...equip3_general_features.models.email_wa_parameter import waParam
import requests, json

headers = {'content-type': 'application/json'}

class VendorDeposit(models.Model):
    _inherit = 'vendor.deposit'

    is_cash_advance_approval_matrix = fields.Boolean(string="Is Cash Advance Approval Matrix", compute='_get_approve_button_from_config')
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    state = fields.Selection(selection_add=[('confirmed', 'Confirmed'),('post', 'Paid')], ondelete={'confirmed': 'cascade', 'post': 'cascade'})


    def _get_approve_button_from_config(self):
        for record in self:
            if record.is_cash_advance:
                is_cash_advance_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_cash_advance_approving_matrix', False)
                record.is_cash_advance_approval_matrix = is_cash_advance_approval_matrix
            else:
                is_vendor_deposit_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_vendor_deposit_approval_matrix', False)
                record.is_vendor_deposit_approval_matrix = is_vendor_deposit_approval_matrix

    @api.onchange('approval_matrix_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            approval_matrix = record.is_cash_advance_approval_matrix if record.is_cash_advance else record.is_vendor_deposit_approval_matrix
            if record.state == 'draft' and approval_matrix:
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
            
    @api.depends('amount', 'company_id', 'branch_id')
    def _get_approval_matrix(self):
        for record in self:
            approval_type = 'cash_advance_approval_matrix' if record.is_cash_advance else 'vendor_deposit_approval_matrix'
            matrix_id = False
            matrix_id = self.env['approval.matrix.accounting'].search([
                ('company_id', '=', record.company_id.id),
                ('branch_id', '=', record.branch_id.id),
                ('min_amount', '<=', record.amount),
                ('max_amount', '>=', record.amount),
                ('approval_matrix_type', '=', approval_type)
            ], limit=1)
            record.approval_matrix_id = matrix_id
            record._compute_approving_matrix_lines()

    def action_reject(self):
        print('move to action_reject_cash_advance, Delete after update')

    def action_reject_cash_advance(self):
        return {
                'type': 'ir.actions.act_window',
                'name': 'Rejected Reason',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'cash.advance.reject',
                'target': 'new',
            }

    @api.model
    def _send_whatsapp_message_cash_advance(self, template_id, approver, url=False, reason=False):
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
            if "${amount}" in string_test:
                string_test = string_test.replace("${amount}", str(record.amount))
            if "${currency}" in string_test:
                string_test = string_test.replace("${currency}", str(record.currency_id.name))
            if "${payment_date}" in string_test:
                string_test = string_test.replace("${payment_date}", fields.Datetime.from_string(record.payment_date).strftime('%d/%m/%Y'))
            if "${create_date}" in string_test:
                string_test = string_test.replace("${create_date}", fields.Datetime.from_string(record.create_date).strftime('%d/%m/%Y'))
            if "${feedback}" in string_test:
                string_test = string_test.replace("${feedback}", reason)
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            phone_num = str(approver.mobile or approver.mobile_phone)
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "")
            wa_sender.set_wa_string(string_test, template_id._name, template_id=template_id)
            wa_sender.send_wa(phone_num)
            
    def action_request_approval(self):
        print('move to action_request_approval_cash_advance, Delete after update')

    def send_request_approval_cash_advance(self):
        for record in self:
            action_id = self.env.ref('equip3_accounting_cash_advance.action_account_cash_advance')
            template_id = self.env.ref('equip3_accounting_cash_advance_extd.email_template_cash_advance_approval_matrix')
            wa_template_id = self.env.ref('equip3_accounting_cash_advance_extd.wa_template_accounting_cash_advance_approval')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=vendor.deposit'
            record.request_partner_id = self.env.user.partner_id.id
            if record.approved_matrix_ids and len(record.approved_matrix_ids[0].user_ids) > 1:
                for approved_matrix_id in record.approved_matrix_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.work_email,
                        'approver_name' : approver.name,
                        'date': date.today(),
                        'submitter' : self.env.user.name,
                        'url' : url,
                        "amount_cash_advance": record.amount,
                        "currency_id_cash_advance": record.currency_id.name,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    record._send_whatsapp_message_cash_advance(wa_template_id, approver, url)
            else:
                approver = record.approved_matrix_ids[0].user_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : approver.work_email,
                    'approver_name' : approver.name,
                    'date': date.today(),
                    'submitter' : self.env.user.name,
                    'url' : url,
                    "amount_cash_advance": record.amount,
                    "currency_id_cash_advance": record.currency_id.name,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                record._send_whatsapp_message_cash_advance(wa_template_id, approver, url)
            record.write({'state' : 'to_approve'})

    def action_request_approval_cash_advance(self):
        for record in self:
            record.send_request_approval_cash_advance()
    
    def action_approve(self):
        print('move to action_approve_cash_advance, Delete after update')

    def action_approve_cash_advance(self):
        for record in self:
            action_id = self.env.ref('equip3_accounting_cash_advance.action_account_cash_advance')
            template_id = self.env.ref('equip3_accounting_cash_advance_extd.email_template_cash_advance_approval_matrix')
            template_id_submitter = self.env.ref('equip3_accounting_cash_advance_extd.email_template_cash_advance_submitter_approval_matrix')
            wa_template_id = self.env.ref('equip3_accounting_cash_advance_extd.wa_template_accounting_cash_advance_approval')
            wa_template_submitted = self.env.ref('equip3_accounting_cash_advance_extd.wa_template_accounting_cash_advance_approved')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=vendor.deposit'
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                    user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    if name != '':
                        name += "\n • %s: Approved" % (self.env.user.name)
                    else:
                        name += "• %s: Approved" % (self.env.user.name)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True})
                        ctx = {
                            'email_from' : self.env.user.company_id.email,
                            'email_to' : record.request_partner_id.email,
                            'approver_name' : record.name,
                            'date': date.today(),
                            'create_date': record.create_date.date(),
                            'submitter' : self.env.user.name,
                            'url' : url,
                            "amount_cash_advance": record.amount,
                            "currency_id_cash_advance": record.currency_id.name,
                        }
                        template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                        record._send_whatsapp_message_cash_advance(wa_template_submitted, record.request_partner_id.user_ids, url)
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
                                    "amount_cash_advance": record.amount,
                                    "currency_id_cash_advance": record.currency_id.name,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                record._send_whatsapp_message_cash_advance(wa_template_id, approving_matrix_line_user, url)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                    'approver_name' : next_approval_matrix_line_id[0].user_ids[0].name,
                                    'date': date.today(),
                                    'submitter' : self.env.user.name,
                                    'url' : url,
                                    "amount_cash_advance": record.amount,
                                    "currency_id_cash_advance": record.currency_id.name,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                record._send_whatsapp_message_cash_advance(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], url)
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r:r.approved)):
                self.action_pay_cash_advance()

    def action_confirm(self):
        for record in self:
            record.write({'state':'confirmed'})