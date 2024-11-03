# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, timedelta, date
from odoo.tools.float_utils import float_is_zero
from itertools import groupby
import requests
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
headers = {'content-type': 'application/json'}
import logging
_logger = logging.getLogger(__name__)


class Purchase(models.Model):
    _inherit = 'purchase.order'

    dp = fields.Boolean("Direct Purchase")
    journal_id = fields.Many2one('account.journal', 'Journal', domain=[('type', 'in', ['bank','cash'])], tracking=True)
    name_dp = fields.Char("DP")
    direct_approval_matrix_id = fields.Many2one('approval.matrix.direct.purchase',string="Direct Purchase Approval Matrix", readonly="1")
    is_approval_matrix_direct = fields.Boolean(compute="_compute_approval_matrix_direct", string="Approving Matrix")
    approved_matrix_direct_ids = fields.One2many('approval.matrix.direct.purchase.line', 'order_id', compute="_compute_approving_direct_matrix_lines", store=True, string="Approved Matrix")
    approved_matrix_direct_id = fields.Many2one('approval.matrix.direct.purchase.line', string="Approved Matrix", compute='_compute_is_approve_button')
    state_direct_on = fields.Selection(related="state", tracking=False)
    state_direct_off = fields.Selection(related="state", tracking=False)
    is_approve_button_direct = fields.Boolean("Show Approve Button", compute='_compute_is_approve_button', store=False)
    control = fields.Boolean("Control")
    qty_limit = fields.Float("Qty Limit")
    budget_limit = fields.Float("Budget Limit")

    @api.constrains('state')
    def set_inv_move(self):
        for rec in self:
            rec._compute_invoice()

    def _compute_is_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_direct_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
            if len(matrix_line) == 0:
                record.is_approve_button_direct = False
                record.approved_matrix_direct_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button_direct = True
                    record.approved_matrix_direct_id = matrix_line_id.id
                else:
                    record.is_approve_button_direct = False
                    record.approved_matrix_direct_id = False
            else:
                record.is_approve_button_direct = False
                record.approved_matrix_direct_id = False

    def _send_whatsapp_message_approval(self, template_id, approver, phone, url, submitter=False):
        for record in self:
            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.request_partner_id.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", submitter)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            phone_num = phone
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "")
            param = {'body': string_test, 'phone': phone_num, 'previewBase64': '', 'title': ''}
            domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
            token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
            try:
                request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
            except ConnectionError:
                raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def _send_qiscus_whatsapp_approval(self, template_id, approver, phone, url, submitter=False):
        for record in self:
            broadcast_template_id = self.env['qiscus.wa.template.content'].search([
                ('language', '=', 'en'),
                ('template_id.name', '=', 'hm_sale_notification_1')
            ], limit=1)
            if not broadcast_template_id:
                raise ValidationError(_("Cannot find Whatsapp template with name = 'hm_sale_notification_1'!"))
            domain = self.env['ir.config_parameter'].get_param('qiscus.api.url')
            token = self.env['ir.config_parameter'].get_param('qiscus.api.secret_key')
            app_id = self.env['ir.config_parameter'].get_param('qiscus.api.appid')
            channel_id = self.env['ir.config_parameter'].get_param('qiscus.api.channel_id')

            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.request_partner_id.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", submitter)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            # message = re.sub(r'\n+', ', ', string_test)
            messages = string_test.split(f'\n')
            message_obj = []
            for pesan in messages:
                message_obj.append({
                    'type': 'text',
                    'text': pesan
                })
            phone_num = phone
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "").replace(" ", "").replace("-", "")
            headers = {
                'content-type': 'application/json',
                'Qiscus-App-Id': app_id,
                'Qiscus-Secret-Key': token
            }
            url = f'{domain}{app_id}/{channel_id}/messages'
            params = {
                "to": phone_num,
                "type": "template",
                "template": {
                    "namespace": broadcast_template_id.template_id.namespace,
                    "name": broadcast_template_id.template_id.name,
                    "language": {
                        "policy": "deterministic",
                        "code": 'en'
                    },
                    "components": [{
                        "type": "body",
                        "parameters": message_obj
                    }]
                }
            }
            try:
                request_server = requests.post(url, json=params, headers=headers, verify=True)
                _logger.info("\nNotification Whatsapp --> Request for Approval:\n-->Header: %s \n-->Parameter: %s \n-->Result: %s" % (headers, params, request_server.json()))
                # if request_server.status_code != 200:
                #     data = request_server.json()
                #     raise ValidationError(f"""{data["error"]["error_data"]["details"]}""")
            except ConnectionError:
                raise ValidationError("Not connect to API Chat Server. Limit reached or not active!")

    def action_request_direct(self):
        is_email_notification_direct_purchase = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation_cont.is_email_notification_direct_purchase')
        is_whatsapp_notification_direct_purchase = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation_cont.is_whatsapp_notification_direct_purchase')
        # is_email_notification_direct_purchase = self.env.company.is_email_notification_direct_purchase
        # is_whatsapp_notification_direct_purchase = self.env.company.is_whatsapp_notification_direct_purchase
        for record in self:
            data = []
            action_id = self.env.ref('equip3_purchase_other_operation_cont.action_direct_purchase')
            template_id = self.env.ref('equip3_purchase_other_operation_cont.email_template_direct_purchase')
            wa_template_id = self.env.ref('equip3_purchase_other_operation_cont.whatsapp_direct_purchase')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=purchase.order'
            record.request_partner_id = self.env.user.partner_id.id
            if record.approved_matrix_direct_ids and len(record.approved_matrix_direct_ids[0].user_ids) > 1:
                for approved_matrix_id in record.approved_matrix_direct_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.email,
                        'approver_name' : approver.name,
                        'requested_by' : self.env.user.name,
                        'product_lines' : data,
                        'date': date.today(),
                        'url' : url,
                    }
                    if is_email_notification_direct_purchase:
                        template_id.with_context(ctx).send_mail(record.id, True)
                    if is_whatsapp_notification_direct_purchase:
                        phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                        # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                        record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
            else:
                approver = record.approved_matrix_direct_ids[0].user_ids[0]
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': approver.partner_id.email,
                    'approver_name': approver.name,
                    'requested_by': self.env.user.name,
                    'product_lines': data,
                    'date': date.today(),
                    'url': url,
                }
                if is_email_notification_direct_purchase:
                    template_id.with_context(ctx).send_mail(record.id, True)
                if is_whatsapp_notification_direct_purchase:
                    phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
            record.check_control()
            record.state = 'waiting_for_approve'

    def action_approve_direct(self):
        is_email_notification_direct_purchase = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation_cont.is_email_notification_direct_purchase')
        is_whatsapp_notification_direct_purchase = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation_cont.is_whatsapp_notification_direct_purchase')
        # is_email_notification_direct_purchase = self.env.company.is_email_notification_direct_purchase
        # is_whatsapp_notification_direct_purchase = self.env.company.is_whatsapp_notification_direct_purchase
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            data = []
            action_id = self.env.ref('equip3_purchase_other_operation_cont.action_direct_purchase')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=purchase.order'
            template_id = self.env.ref('equip3_purchase_other_operation_cont.email_template_direct_purchase_approval')
            approved_template_id = self.env.ref('equip3_purchase_other_operation_cont.email_template_direct_purchase_approved')
            wa_template_id = self.env.ref('equip3_purchase_other_operation_cont.whatsapp_direct_purchase_approval')
            wa_approved_template_id = self.env.ref('equip3_purchase_other_operation_cont.whatsapp_direct_purchase_approved')
            user = self.env.user
            if record.is_approve_button_direct and record.approved_matrix_direct_id:
                approval_matrix_line_id = record.approved_matrix_direct_id
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
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True, 'approver_state': 'approved'})
                        next_approval_matrix_line_id = sorted(record.approved_matrix_direct_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        approver_name = ' and '.join(approval_matrix_line_id.mapped('user_ids.name'))
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': approving_matrix_line_user.partner_id.email,
                                    'user_name': approving_matrix_line_user.name,
                                    'approver_name': ','.join(approval_matrix_line_id.user_ids.mapped('name')),
                                    'url': url,
                                    'submitter' : approver_name,
                                    'product_lines': data,
                                    'date': date.today(),
                                }
                                if is_email_notification_direct_purchase:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_whatsapp_notification_direct_purchase:
                                    phone_num = str(approving_matrix_line_user.partner_id.mobile) or str(approving_matrix_line_user.partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, approving_matrix_line_user, phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id, approving_matrix_line_user,
                                                                           phone_num, url, submitter=approver_name)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                    'user_name': next_approval_matrix_line_id[0].user_ids[0].name,
                                    'approver_name': ','.join(approval_matrix_line_id.user_ids.mapped('name')),
                                    'url': url,
                                    'submitter' : approver_name,
                                    'product_lines': data,
                                    'date': date.today(),
                                }
                                if is_email_notification_direct_purchase:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_whatsapp_notification_direct_purchase:
                                    phone_num = str(next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile) or str(next_approval_matrix_line_id[0].user_ids[0].partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id,
                                                                           next_approval_matrix_line_id[0].user_ids[0],
                                                                           phone_num, url, submitter=approver_name)
                    else:
                        approval_matrix_line_id.write({'approver_state': 'pending'})
            if len(record.approved_matrix_direct_ids) == len(record.approved_matrix_direct_ids.filtered(lambda r:r.approved)):
                record.write({'state': 'rfq_approved'})
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.request_partner_id.email,
                    'date': date.today(),
                    'url' : url,
                }
                if is_email_notification_direct_purchase:
                    approved_template_id.sudo().with_context(ctx).send_mail(record.id, True)
                if is_whatsapp_notification_direct_purchase:
                    phone_num = str(record.request_partner_id.mobile) or str(record.request_partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_approved_template_id, record.request_partner_id, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_approved_template_id, record.request_partner_id,
                                                           phone_num, url)

    def button_confirm(self):
        self.check_control()
        res = super(Purchase, self).button_confirm()
        return res

    def button_approve(self, force=False):
        res = super(Purchase, self).button_approve(force=force)
        is_good_services_order = self.env['ir.config_parameter'].sudo().get_param('is_good_services_order', False)
        # is_good_services_order = self.env.company.is_good_services_order
        for record in self:
            if record.dp and not record.is_goods_orders:
                inv = record.create_services_order_invoice()
            elif record.dp and record.picking_ids and record.is_goods_orders:
                for picking_id in record.picking_ids:
                    picking_id.action_confirm()
                    picking_id.action_assign()
                    for move_id in picking_id.move_ids_without_package:
                        move_id.quantity_done = move_id.product_uom_qty
                    picking_id.with_context(
                        skip_immediate=True, skip_backorder=True
                    ).button_validate()
                inv = record.create_services_order_invoice()
            else:
                inv = record.invoice_ids
            if inv:
                for invoice in inv:
                    if invoice.amount_total > 0:
                        invoice.invoice_date = datetime.now()
                        invoice.action_post()
                        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
                            'journal_id': self.journal_id.id,
                            'payment_date': datetime.now().date(),
                            'amount': invoice.amount_total,
                            'branch_id': self.env['res.branch'].search([('company_id', '=', self.env.company.id)], limit=1).id,
                        })
                        payments._create_payments()

        return res

    def create_services_order_invoice(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        for order in self:
            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            print (">invoice_vals", invoice_vals)
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                invoice_vals['invoice_line_ids'].append((0, 0, line._prepare_account_move_line()))
            invoice_vals_list.append(invoice_vals)

        # 2) group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': ', '.join(origins),
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list
        # 3) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

        return moves

    def check_control(self):
        for rec in self:
            if rec.dp:
                IrConfigParam = self.env['ir.config_parameter'].sudo()
                control = IrConfigParam.get_param('equip3_purchase_other_operation_cont.direct_control')
                # control = self.env.company.direct_control
                if control:
                    budget_limit = IrConfigParam.get_param('equip3_purchase_other_operation_cont.budget_limit')
                    # budget_limit = self.env.company.budget_limit
                    if rec.amount_total > float(budget_limit):
                        raise ValidationError(_("The amount total is cannot greater than %s") % budget_limit)


    @api.depends('direct_approval_matrix_id')
    def _compute_approving_direct_matrix_lines(self):
        if self.direct_approval_matrix_id and self.dp:
            data = [(5, 0, 0)]
            for record in self:
                if record.state in ('draft', 'sent'):
                    counter = 1
                    record.approved_matrix_direct_ids = []
                    for line in record.direct_approval_matrix_id.approval_matrix_direct_purchase_line_ids:
                        data.append((0, 0, {
                            'sequence' : counter,
                            'user_ids' : [(6, 0, line.user_ids.ids)],
                            'minimum_approver' : line.minimum_approver,
                        }))
                        counter += 1
                    record.approved_matrix_direct_ids = data

    def approval_matrix_direct(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        approval = IrConfigParam.get_param('is_direct_purchase_approval_matrix')
        control = IrConfigParam.get_param('equip3_purchase_other_operation_cont.direct_control')
        qty_limit = IrConfigParam.get_param('equip3_purchase_other_operation_cont.qty_limit')
        budget_limit = IrConfigParam.get_param('equip3_purchase_other_operation_cont.budget_limit')
        # approval = self.env.company.is_direct_purchase_approval_matrix
        # control = self.env.company.direct_control
        # qty_limit = self.env.company.qty_limit
        # budget_limit = self.env.company.budget_limit
        for record in self:
            record.write({
                'is_approval_matrix_direct': approval,
                'control': control,
                'qty_limit': qty_limit,
                'budget_limit': budget_limit
            })

    @api.onchange('name')
    def onchange_purchase_name(self):
        self._compute_approval_matrix_direct()
        res = super(Purchase, self).onchange_purchase_name()
        return res

    @api.model
    def action_direct_purchase_order_menu(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
        # is_good_services_order = self.env.company.is_good_services_order
        direct_po_action = self.env.ref('equip3_purchase_other_operation_cont.action_approval_matrix_direct_purchase')
        if is_good_services_order:
            direct_po_action.write({
                'context': {'direct_order_type_invisible': False}
            })
        else:
            direct_po_action.write({
                'context': {'direct_order_type_invisible': True}
            })


    @api.depends('amount_untaxed','approval_matrix_id')
    def _compute_approval_matrix_direct(self):
        for record in self:
            record.direct_approval_matrix_id = False
            record.approval_matrix_direct()
            if record.dp:
                record.write({
                    'approval_matrix_id': False,
                    'is_approval_matrix': False,
                    'approved_matrix_ids': [(6, 0, [])]
                })
            if record.is_approval_matrix_direct:
                if record.dp and record.is_goods_orders:
                    approval_matrix_id = self.env['approval.matrix.direct.purchase'].search([
                        ('minimum_amt', '<=', record.amount_untaxed),
                        ('maximum_amt', '>=', record.amount_untaxed),
                        ('branch_id', '=', record.branch_id.id),
                        ('company_id', '=', record.company_id.id),
                        ('order_type', '=', "goods_order")
                        ], limit=1)
                    record.direct_approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
                elif record.dp and record.is_services_orders:
                    approval_matrix_id = self.env['approval.matrix.direct.purchase'].search([
                        ('minimum_amt', '<=', record.amount_untaxed),
                        ('maximum_amt', '>=', record.amount_untaxed),
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('order_type', '=', "services_order")
                        ], limit=1)
                    record.direct_approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
                else:
                    approval_matrix_id = self.env['approval.matrix.direct.purchase'].search([
                        ('minimum_amt', '<=', record.amount_untaxed),
                        ('maximum_amt', '>=', record.amount_untaxed),
                        ('branch_id', '=', record.branch_id.id),
                        ('company_id', '=', record.company_id.id)
                        ], limit=1)
                    record.direct_approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False

    @api.model
    def create(self, vals):
        if 'dp' in vals:
            if vals['dp']:
                vals['name'] = self.env['ir.sequence'].next_by_code('direct.purchase.sequence.rfq')
        res = super(Purchase, self).create(vals)
        if res.dp:
            name = False
            if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':
            # if self.env.company.is_good_services_order:
                if res.is_goods_orders:
                    name = self.env['ir.sequence'].next_by_code('direct.purchase.sequence.dp.new.goods')
                elif res.is_services_orders:
                    name = self.env['ir.sequence'].next_by_code('direct.purchase.sequence.dp.new.services')
            else:
                name = self.env['ir.sequence'].next_by_code('direct.purchase.sequence.dp.new')
            res.name = name
            res.name_dp = name
            res.approved_matrix_ids = [(6, 0, [])]
        return res

    def write(self, vals):
        if 'state' in vals and self.dp and 'name' in vals:
            if vals['state'] in ('purchase', 'done'):
                vals['name'] = self.name_dp
        res = super(Purchase, self).write(vals)
        return res

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    dp_line = fields.Boolean(related="order_id.dp")

    @api.onchange('dp_line')
    def onchange_product_type(self):
        product_domain = {}
        context = dict(self.env.context) or {}
        if self.order_id.partner_id.vendor_product_categ_ids:
            domain_product_template_id = []
            vendor_categ = self.order_id.partner_id.vendor_product_categ_ids
            if vendor_categ:
                for x in vendor_categ:
                    domain_product_template_id.extend(x.ids)
                categs = self.env['product.category'].search([('id', 'in', domain_product_template_id)]) 
                categ_type = categs.mapped('stock_type')
                product_domain = {'domain': {'product_template_id': [('type', 'in', categ_type)]}}
                return product_domain
            
        if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order'):
        # if self.env.company.is_good_services_order:
            if self.dp_line and context.get('goods_order'):
                product_domain = {'domain': {'product_template_id': [('can_be_direct','=',True), ('type', 'in', ['consu', 'product']), ('purchase_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id)]}}
            elif self.dp_line and context.get('services_good'):
                product_domain = {'domain': {'product_template_id': [('can_be_direct','=',True), ('type', 'in', ['service']), ('purchase_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id)]}}
            elif self.dp_line and context.get('assets_orders'):
                product_domain = {'domain': {'product_template_id': [('can_be_direct','=',True), ('type', 'in', ['asset']), ('purchase_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id)]}}
            elif self.dp_line and context.get('rentals_orders'):
                product_domain = {'domain': {'product_template_id': [('can_be_direct','=',True), ('is_rented', '=', True), ('purchase_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id)]}}
        else:
            if not self.dp_line:
                product_domain = {'domain': {'product_template_id': [('purchase_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id)]}}
            else:
                product_domain = {'domain': {'product_template_id': [('can_be_direct','=',True), ('purchase_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id)]}}

        # if self.dp_line:
        #     product_domain = {'domain': {'product_template_id': [('can_be_direct', '=', True), ('is_rented', '=', True), ('purchase_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id)]}}
        return product_domain

    @api.onchange('product_qty')
    def check_qty_and_limit(self):
        for rec in self:
            if rec.order_id.dp and rec.product_template_id:
                IrConfigParam = self.env['ir.config_parameter'].sudo()
                control = IrConfigParam.get_param('equip3_purchase_other_operation_cont.direct_control')
                # control = self.env.company.direct_control
                if control:
                    qty_limit = IrConfigParam.get_param('equip3_purchase_other_operation_cont.qty_limit')
                    budget_limit = IrConfigParam.get_param('equip3_purchase_other_operation_cont.budget_limit')
                    if float(qty_limit) < 1 and float(budget_limit) < 1:
                        raise ValidationError(_("Please set the Direct Purchase Budget Controller!"))
                    if float(qty_limit) >= 1 and float(budget_limit) < 1:
                        raise ValidationError(_("Please set the Budget Limit!"))
                    if float(qty_limit) < 1 and float(budget_limit) >= 1:
                        raise ValidationError(_("Please set the Quantity Limit!"))
                    # if rec.product_qty > float(qty_limit):
                    #     raise ValidationError(_("The quantity is cannot greater than %s") % qty_limit)

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    branch_id = fields.Many2one('res.branch')
