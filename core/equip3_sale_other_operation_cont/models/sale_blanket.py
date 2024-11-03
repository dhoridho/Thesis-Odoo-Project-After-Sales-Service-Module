# -*- coding: utf-8 -*-
import re

from odoo import models, fields, api, tools, _
from datetime import datetime,timedelta,date
from odoo.exceptions import ValidationError, Warning
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, float_compare, float_round
import requests
import logging
import json
_logger = logging.getLogger(__name__)

headers = {'content-type': 'application/json'}

class saleBlanket(models.Model):

    _name = 'saleblanket.saleblanket'
    _inherit = ['saleblanket.saleblanket', 'portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    expiry_date = fields.Datetime('Expiry Date', tracking=True, required=True)
    creation_date = fields.Datetime(string='Creation Date', default=datetime.now(), tracking=True, readonly=True)
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True, tracking=True)
    order_line_count = fields.Integer(string="Order Line", compute='order_line_calc', store=True, tracking=True)
    state = fields.Selection(selection_add=[
        ('new','New'),
        ('to_approve','Waiting For Approval'),
        ('approved','Blanket Order Approved'),
        ('rejected','Blanket Order Rejected'),
        ('open', 'Running'),
        ('done', 'Closed'),
        ('cancel', 'Cancelled'),
        ('expired', 'Expired'),
    ], string='Status', readonly=True, default='new', tracking=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency', readonly=True, store=True)
    state1 = fields.Selection(related='state', tracking=False)
    state2 = fields.Selection(related='state', tracking=False)
    state3 = fields.Selection(related='state', tracking=False)
    bo_state = fields.Selection(related='state', tracking=False)
    bo_state_1 = fields.Selection(related='state', tracking=False)
    company_id = fields.Many2one('res.company', default=lambda self:self.env.company, tracking=True, store=True, readonly=True)
    current_company=fields.Many2one('res.company',string="Company", default=lambda self: self.env.company)
    branch_id = fields.Many2one('res.branch', required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], string="Branch", tracking=True)
    days_left = fields.Integer("Days Left")
    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag', string='Analytic Group', domain="[('company_id', '=', company_id)]", required=False, tracking=True)
    order_line_ids = fields.One2many('orderline.orderline','reverse_id', tracking=True)
    qty = fields.Float("All Qty", store=True)
    delivery_qty = fields.Float("Delivery Qty", store=True)
    remaining_qty = fields.Float("Remaining Qty", store=True)
    qty_invoiced = fields.Float("Invoiced Qty", store=True)
    reason = fields.Text("Force Done Reason", tracking=True)
    delivery_status = fields.Boolean("status")
    approving_matrix_bo_sale_id = fields.Many2one('approval.matrix.sale.order', string="Approval Matrix", compute='_compute_approving_customer_matrix_bo', store=True)
    is_bo_approval_matrix = fields.Boolean(string="Bo Matrix", store=False, compute='_compute_is_bo_approval_matrix')
    is_approval_matrix_filled = fields.Boolean(string="Custome Matrix", store=False, compute='_compute_approval_matrix_filled')
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.sale.order.lines', string='Sale Approval Matrix Line', compute='_get_approve_button', store=False)
    approved_matrix_ids = fields.One2many('approval.matrix.sale.order.lines', 'bo_order_id', store=True, string="Approved Matrix Line", compute='_compute_approving_matrix_lines')
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    analytic_accounting = fields.Boolean("Analyic Account", compute="get_analytic_accounting", store=True)
    invoice_address = fields.Many2one(domain="[('parent_id', '=', partner_id),('type','=','invoice')]")
    delivery_address = fields.Many2one(domain="[('parent_id', '=', partner_id),('type','=','delivery')]")
    is_product_filled = fields.Boolean(string='Is Product Filled', compute='_onchange_is_product_filled')
    is_active_company = fields.Boolean(
        string="Active Company", store=False, search="_search_is_active_company")
    filter_branch = fields.Char(string="Filter Branch", compute='_compute_filter_branch', store=False)
    
    @api.depends('company_id')
    def _compute_filter_branch(self):
        for rec in self:
            rec.filter_branch = json.dumps(
                [('id', 'in', self.env.branches.ids), ('company_id', '=', self.company_id.id)])

    def action_print(self):
        return self.env.ref('equip3_sale_other_operation_cont.report_sale_blanket').report_action(self)


    def _search_is_active_company(self, operator, value):
        company_id = self.env.company.id
        return [('current_company', '=', company_id)]

    @api.depends('order_line_ids.price_subtotal')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.depends('approving_matrix_bo_sale_id')
    def _compute_approval_matrix_filled(self):
        for record in self:
            record.is_approval_matrix_filled = False
            if record.approving_matrix_bo_sale_id:
                record.is_approval_matrix_filled = True

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
            if len(matrix_line) == 0:
                record.is_approve_button = False
                record.approval_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_name_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button = True
                    record.approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button = False
                    record.approval_matrix_line_id = False
            else:
                record.is_approve_button = False
                record.approval_matrix_line_id = False

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        fields_to_hide = ['state1', 'state2', 'state3', 'bo_state', 'bo_state_1', 'delivery_status']
        res = super(saleBlanket, self).fields_get()
        for field in fields_to_hide:
            res[field]['searchable'] = False
        return res

    @api.depends('partner_id')
    def _compute_is_bo_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_bo_approval_matrix = IrConfigParam.get_param('is_bo_approval_matrix')
        for record in self:
            record.is_bo_approval_matrix = is_bo_approval_matrix

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(saleBlanket, self).onchange_partner_id()
        self._compute_is_bo_approval_matrix()
        self._get_approve_button()
        self._compute_approval_matrix_filled()
        return res

    @api.depends('approving_matrix_bo_sale_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.is_bo_approval_matrix:
                record.approved_matrix_ids = []
                counter = 1
                record.approved_matrix_ids = []
                for rec in record.approving_matrix_bo_sale_id:
                    for line in rec.approver_matrix_line_ids:
                        data.append((0, 0, {
                            'sequence' : counter,
                            'user_name_ids' : [(6, 0, line.user_name_ids.ids)],
                            'minimum_approver' : line.minimum_approver,
                            'approval_type': rec.config,
                        }))
                        counter += 1
                record.approved_matrix_ids = data

    @api.depends('order_line_ids', 'order_line_ids.price_subtotal', 'branch_id', 'currency_id')
    def _compute_approving_customer_matrix_bo(self):
        for rec in self:
            if rec.is_bo_approval_matrix:
                rec.approving_matrix_bo_sale_id = False
                for record in rec:
                    sub_total = sum(rec.order_line_ids.mapped('price_subtotal'))
                    domain = [('config', '=', 'total_amt'),
                                ('minimum_amt', '<=', sub_total),
                                ('maximum_amt', '>=', sub_total),
                                ('currency_id', '=', rec.currency_id.id)]
                    if record.branch_id:
                        domain.append(('branch_id', '=', record.branch_id.id))
                    else:
                        domain.append(('company_id', '=', record.company_id.id))
                    matrix_id = self.env['approval.matrix.sale.order'].search(domain, limit=1)
                    record.approving_matrix_bo_sale_id = matrix_id
                    record._get_approve_button()
            else:
                rec.approving_matrix_bo_sale_id = False

    def action_request_for_approval_bo(self):
        for record in self:
            record.write({'state': 'to_approve'})

            get_bo_approval = self.env['ir.config_parameter'].get_param(
                'equip3_sale_other_operation_cont.bo_approval_email_notify')
            get_bo_approval_wa = self.env['ir.config_parameter'].get_param(
                'equip3_sale_other_operation_cont.bo_approval_wa_notify')
            if get_bo_approval or get_bo_approval_wa:
                sorted_matrix_id = sorted(record.approved_matrix_ids)
                for matrix_id in sorted_matrix_id:
                    if matrix_id.sequence == 1:
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        url = base_url + '/web#id=' + str(record.id) + '&view_type=form&model=saleblanket.saleblanket'
                        for user_id in matrix_id.user_name_ids:
                            ctx = {
                                'approver_name': user_id.name,
                                'last_approved': '',
                                'email_to': user_id.email,
                                'date': date.today(),
                                'url': url
                            }
                            if get_bo_approval:
                                template_id = self.env.ref('equip3_sale_other_operation_cont.email_template_bo_approval_email_notification').id
                                template = self.env['mail.template'].browse(template_id)
                                template.with_context(ctx).send_mail(record.id, True)

                            if get_bo_approval_wa:
                                last_approver = ''
                                subject = 'Reminder for Blanket Order Approval'
                                wa_template_id = self.env.ref(
                                    'equip3_sale_other_operation_cont.email_template_bo_approval_email_notification_wa')

                                phone_num = str(user_id.partner_id.mobile) or str(user_id.partner_id.phone)
                                # record._send_whatsapp_message_approval(wa_template_id, user_id, last_approver, subject, phone_num, url,
                                #                                        submitter=user_id.name)
                                record._send_qiscus_whatsapp_approval(wa_template_id, user_id, last_approver, subject, phone_num, url,
                                                                       submitter=user_id.name)

    def action_approved_bo(self):
        for record in self:
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_name_ids.ids and \
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
                        # next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        # if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].approver) > 1:
                        #     pass
                        get_bo_approval = self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_approval_email_notify')
                        get_bo_approval_wa = self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_approval_wa_notify')
                        if get_bo_approval or get_bo_approval_wa:
                            last_approver = re.sub(': Approved\n*', '', name)
                            last_approver = re.sub('•', 'and', last_approver)
                            last_approver = last_approver[4:]
                            last_approver = last_approver.replace(" and ", ", ", approval_matrix_line_id.minimum_approver-2)
                            next_seq = approval_matrix_line_id.sequence + 1
                            sorted_matrix_id = sorted(record.approved_matrix_ids)
                            for matrix_id in sorted_matrix_id:
                                if matrix_id.sequence == next_seq:
                                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                                    url = base_url + '/web#id=' + str(record.id) + '&view_type=form&model=saleblanket.saleblanket'

                                    for user_id in matrix_id.user_name_ids:
                                        ctx = {
                                            'approver_name': user_id.name,
                                            'last_approved': last_approver,
                                            'email_to': user_id.email,
                                            'date': date.today(),
                                            'url': url
                                        }
                                        if get_bo_approval:
                                            template_id = self.env.ref('equip3_sale_other_operation_cont.email_template_bo_approval_email_notification').id
                                            template = self.env['mail.template'].browse(template_id)
                                            template.with_context(ctx).send_mail(record.id, True)

                                        if get_bo_approval_wa:
                                            last_approver = 'For the Information, the previous approver was '+last_approver+'.'
                                            subject = 'Reminder for Blanket Order Approval'
                                            wa_template_id = self.env.ref('equip3_sale_other_operation_cont.email_template_bo_approval_email_notification_wa')

                                            phone_num = str(user_id.partner_id.mobile) or str(user_id.partner_id.phone)
                                            # record._send_whatsapp_message_approval(wa_template_id, user_id, last_approver, subject, phone_num, url, submitter=user_id.name)
                                            record._send_qiscus_whatsapp_approval(wa_template_id, user_id, last_approver, subject, phone_num, url, submitter=user_id.name)
                    else:
                        approval_matrix_line_id.write({'approver_state': 'pending'})
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r:r.approved)):
                record.write({'state': 'approved'})

                get_bo_approval = self.env['ir.config_parameter'].get_param(
                    'equip3_sale_other_operation_cont.bo_approval_email_notify')
                get_bo_approval_wa = self.env['ir.config_parameter'].get_param(
                    'equip3_sale_other_operation_cont.bo_approval_wa_notify')
                if get_bo_approval or get_bo_approval_wa:
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    url = base_url + '/web#id=' + str(record.id) + '&view_type=form&model=saleblanket.saleblanket'

                    ctx = {
                        'requester_name': record.user_id.partner_id.name,
                        'email_to': record.user_id.partner_id.email,
                        'date': date.today(),
                        'url': url
                    }
                    if get_bo_approval:
                        template_id = self.env.ref(
                        'equip3_sale_other_operation_cont.email_template_bo_approval_has_been_approved').id
                        template = self.env['mail.template'].browse(template_id)
                        template.with_context(ctx).send_mail(record.id, True)

                    if get_bo_approval_wa:
                        last_approver = ''
                        subject = 'Reminder for Blanket Order Approval has been Approved'
                        wa_template_id = self.env.ref(
                            'equip3_sale_other_operation_cont.email_template_bo_approval_has_been_approved_wa')

                        phone_num = str(record.user_id.partner_id.mobile) or str(record.user_id.partner_id.phone)
                        # record._send_whatsapp_message_approval(wa_template_id, record.user_id.partner_id, last_approver, subject, phone_num, url,
                        #                                        submitter=record.partner_id.name)
                        record._send_qiscus_whatsapp_approval(wa_template_id, record.user_id.partner_id, last_approver, subject, phone_num, url,
                                                               submitter=record.partner_id.name)

    def action_reject_bo(self):
        for record in self:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Reject Reason',
                    'res_model': 'bo.approval.matrix.sale.reject',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }

    def to_draft(self):
        res = super(saleBlanket, self).to_draft()
        for rec in self:
            for line in rec.approved_matrix_ids:
                line.write({'last_approved': False, 'approved': False, 'state_char': False, 'time_stamp': False, 'feedback': False, 'approved_users': False})
        return res

    @api.onchange('order_line_ids')
    def _set_qty_bo(self):
        for res in self:
            qty = 0
            r_qty = 0
            d_qty = 0
            i_qty = 0
            status = False
            for line in res.order_line_ids:
                qty += line.quantity
                d_qty += line.delivered_qty
                r_qty += line.remaining_quantity
                i_qty += line.qty_invoiced
                if d_qty < qty:
                    status = True
                else:
                    status = False
                line.undelivered_qty = line.quantity - line.delivered_qty
            res.update({
                'qty': qty,
                'delivery_qty': d_qty,
                'remaining_qty': r_qty,
                'qty_invoiced': i_qty,
                'delivery_status': status
            })

    def action_force_done(self, reason):
        for res in self:
            res.update({
                'state': 'done',
                'reason': reason
            })

    # @api.onchange('analytic_tag_ids')
    # def set_analytic_tag(self):
    #   for res in self:
    #       for line in res.order_line_ids:
    #           line.analytic_tag_ids = res.analytic_tag_ids

    @api.onchange('order_line_ids.product_id')
    def _onchange_is_product_filled(self):
        if self.order_line_ids:
            if self.order_line_ids.product_id:
                self.is_product_filled = True
        else:
            self.is_product_filled = False

    @api.model
    def create(self, vals):
        vals['name'] = "BO/" + str(datetime.strftime(date.today(), "%y/%m/%d")) + "/" + self.env['ir.sequence'].next_by_code('blanket.order.seq.1')
        res = super(saleBlanket, self).create(vals)
        return res

    def action_wiz_1(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Force Done Wizard'),
            'res_model': 'force.done.memory',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_sale_other_operation_cont.force_done_memory_form1').id,
            'target': 'new',
            'context': {
                'default_blanket_id': self.id,
                'default_qty': self.qty,
                'default_remaining_qty': self.remaining_qty,
            },
        }

    @api.depends('order_line_ids')
    def order_line_calc(self):
        for record in self:
            record.order_line_count = len(record.order_line_ids)

    @api.onchange('account_tag_ids')
    def set_account_group_lines(self):
        for res in self:
            for line in res.order_line_ids:
                line.analytic_tag_ids = res.analytic_tag_ids

    @api.depends('company_id')
    def get_analytic_accounting(self):
        for res in self:
            res.analytic_accounting = res.user_has_groups('analytic.group_analytic_tags')

    @api.model
    def default_get(self, fields):
        res = super(saleBlanket, self).default_get(fields)
        exp_date = self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_expiry_date') or 30
        res.update({
            'expiry_date': datetime.now() + timedelta(days=int(exp_date))
        })
        analytic_priority_ids = self.env['analytic.priority'].search([], order="priority")
        for analytic_priority in analytic_priority_ids:
            if analytic_priority.object_id == 'user' and self.env.user.analytic_tag_ids:
                res.update({
                    'analytic_tag_ids': [(6, 0, self.env.user.analytic_tag_ids.ids)]
                })
                break
            elif analytic_priority.object_id == 'branch' and self.env.user.branch_id.analytic_tag_ids:
                res.update({
                    'analytic_tag_ids': [(6, 0, self.env.user.branch_id.analytic_tag_ids.ids)]
                })
                break
        return res

    @api.depends("order_line_ids")
    def _compute_max_line_sequence(self):
        """Allow to know the highest sequence entered in move lines.
        Then we add 1 to this value for the next sequence, this value is
        passed to the context of the o2m field in the view.
        So when we create new move line, the sequence is automatically
        incremented by 1. (max_sequence + 1)
        """
        for bo in self:
            bo.max_line_sequence = max(bo.mapped("order_line_ids.sequence") or [0]) + 1

    max_line_sequence = fields.Integer(
        string="Max sequence in lines", compute="_compute_max_line_sequence"
    )

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.order_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        return super(saleBlanket, self.with_context(keep_line_sequence=True)).copy(default)

    def button_cancel(self):
        res = super(saleBlanket, self).button_cancel()
        self.state = 'cancel'
        return res

    def done_bo(self):
        for res in self:
            error = []
            for line in res.order_line_ids:
                if line.delivered_qty < line.quantity:
                    error.append(line.id)
            if error:
                raise ValidationError('The delivered quantity is not in accordance with the agreed quantity')
            else:
                res.state = 'done'

    def _auto_done_bo(self):
        template_before = self.env.ref('equip3_sale_other_operation_cont.email_template_bo_befor_expiry_reminder')
        template_on_exp = self.env.ref('equip3_sale_other_operation_cont.email_template_bo_expiry_reminder')
        before = self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_before_exp_notify')
        on_exp = self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_on_date_notify')
        before_exp = self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_days_before_exp_notify') or 0
        bo = self.env['saleblanket.saleblanket'].search([('state', 'in', ['new', 'open'])])
        for res in bo:
            if res.state == 'new' and res.expiry_date:
                if date.today() >= res.expiry_date.date():
                    if on_exp:
                        message_composer = self.env['mail.compose.message'].with_context(
                            default_use_template=bool(template_on_exp),
                            mark_so_as_sent=True,
                            custom_layout='mail.mail_notification_paynow',
                            proforma=self.env.context.get('proforma', False),
                            force_email=True,
                        ).create({
                            'res_id': res.id,
                            'template_id': template_on_exp and template_on_exp.id or False,
                            'model': 'saleblanket.saleblanket',
                            'composition_mode': 'comment'})

                        # Simulate the onchange (like trigger in form the view)
                        update_values = message_composer.onchange_template_id(template_on_exp.id, 'comment', 'saleblanket.saleblanket', res.id)['value']
                        message_composer.write(update_values)

                        message_composer.send_mail()
                        mail_message_id = self.env['mail.message'].search([('res_id', '=', res.id), ('model', '=', 'saleblanket.saleblanket')], limit=1)
                        mail_message_id.res_id = 0
                        res.message_post(body=_("Email has been sent to %s for Blanket Order expiry notification") % res.user_id.name)
                    res.state = 'expired'
                if before:
                    if date.today() + timedelta(days=int(before_exp)) == res.expiry_date.date():
                        res.days_left = int(before_exp)
                        message_composer = self.env['mail.compose.message'].with_context(
                            default_use_template=bool(template_before),
                            mark_so_as_sent=True,
                            custom_layout='mail.mail_notification_paynow',
                            proforma=self.env.context.get('proforma', False),
                            force_email=True,
                        ).create({
                            'res_id': res.id,
                            'template_id': template_before and template_before.id or False,
                            'model': 'saleblanket.saleblanket',
                            'composition_mode': 'comment'})

                        # Simulate the onchange (like trigger in form the view)
                        update_values = message_composer.onchange_template_id(template_before.id, 'comment', 'saleblanket.saleblanket', res.id)['value']
                        message_composer.write(update_values)

                        message_composer.send_mail()
                        mail_message_id = self.env['mail.message'].search([('res_id', '=', res.id), ('model', '=', 'saleblanket.saleblanket')], limit=1)
                        mail_message_id.res_id = 0
                        res.message_post(body=_("Email has been sent to %s for Blanket Order expiry reminder") % res.user_id.name)
            elif res.state == 'open' and res.expiry_date:
                if date.today() >= res.expiry_date.date():
                    error = []
                    for line in res.order_line_ids:
                        if line.delivered_qty < line.quantity:
                            error.append(line.id)
                    if error:
                        if on_exp:
                            message_composer = self.env['mail.compose.message'].with_context(
                                default_use_template=bool(template_on_exp),
                                mark_so_as_sent=True,
                                custom_layout='mail.mail_notification_paynow',
                                proforma=self.env.context.get('proforma', False),
                                force_email=True,
                            ).create({
                                'res_id': res.id,
                                'template_id': template_on_exp and template_on_exp.id or False,
                                'model': 'saleblanket.saleblanket',
                                'composition_mode': 'comment'})

                            # Simulate the onchange (like trigger in form the view)
                            update_values = message_composer.onchange_template_id(template_on_exp.id, 'comment', 'saleblanket.saleblanket', res.id)['value']
                            message_composer.write(update_values)

                            message_composer.send_mail()
                            mail_message_id = self.env['mail.message'].search([('res_id', '=', res.id), ('model', '=', 'saleblanket.saleblanket')], limit=1)
                            mail_message_id.res_id = 0
                            res.message_post(body=_("Email has been sent to %s for Blanket Order expiry notification") % res.user_id.name)
                        res.state = 'expired'
                    else:
                        res.state = 'done'
                if before:
                    if date.today() + timedelta(days=int(before_exp)) == res.expiry_date.date():
                        res.days_left = int(before_exp)

                        message_composer = self.env['mail.compose.message'].with_context(
                            default_use_template=bool(template_before),
                            mark_so_as_sent=True,
                            custom_layout='mail.mail_notification_paynow',
                            proforma=self.env.context.get('proforma', False),
                            force_email=True,
                        ).create({
                            'res_id': res.id,
                            'template_id': template_before and template_before.id or False,
                            'model': 'saleblanket.saleblanket',
                            'composition_mode': 'comment'})

                        # Simulate the onchange (like trigger in form the view)
                        update_values = message_composer.onchange_template_id(template_before.id, 'comment', 'saleblanket.saleblanket', res.id)['value']
                        message_composer.write(update_values)

                        message_composer.send_mail()
                        mail_message_id = self.env['mail.message'].search([('res_id', '=', res.id), ('model', '=', 'saleblanket.saleblanket')], limit=1)
                        mail_message_id.res_id = 0
                        res.message_post(body=_("Email has been sent to %s for Blanket Order expiry reminder") % res.user_id.name)

    def get_full_url(self):
        for res in self:
            base_url = request.env['ir.config_parameter'].get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (res.id, res._name)
            return base_url

    def _send_whatsapp_message_approval(self, template_id, approver, last_approver, subject, phone, url, submitter=False):
        for record in self:
            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${subject}" in string_test:
                string_test = string_test.replace("${subject}", subject)
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.user_id.partner_id.name)
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.user_id.partner_id.name)
            if "${last_approved}" in string_test:
                if last_approver:
                    string_test = string_test.replace("${last_approved}", last_approver+"\n")
                else:
                    string_test = string_test.replace("${last_approved}", f"\n")
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
                    # connector_id.ca_request('post', 'sendMessage', param)

    def _send_qiscus_whatsapp_approval(self, template_id, approver, last_approver, subject, phone, url, submitter=False):
        self.ensure_one()
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
            if "${subject}" in string_test:
                string_test = string_test.replace("${subject}", subject)
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.user_id.partner_id.name)
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.user_id.partner_id.name)
            if "${last_approved}" in string_test:
                if last_approver:
                    string_test = string_test.replace("${last_approved}", last_approver)
                else:
                    string_test = string_test.replace("${last_approved}", "")
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


class Branch(models.Model):
    _inherit = 'saleblanket.saleblanket'

    @api.model
    def default_get(self, fields):
        res = super(saleBlanket, self).default_get(fields)
        user_analytics = self.env.user.analytic_tag_ids
        company_id = self.env.company.id
        analytics = []
        for tag in user_analytics:
            if tag.company_id.id == company_id:
                analytics.append(tag.id)
        res.update({
        'analytic_tag_ids': analytics
        })
        return res


class Orderline(models.Model):
    _inherit="orderline.orderline"

    ordered_qty = fields.Float('Ordered Qty', readonly=True)
    delivered_qty = fields.Float('Delivered Qty', readonly=True)
    qty_invoiced = fields.Float('Invoiced Qty', readonly=True)
    undelivered_qty = fields.Float("Undelivered Qty", readonly=True)
    sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence')
    sequence2 = fields.Integer(
        string="No",
        related="sequence",
        readonly=True,
        store=True
    )
    company_id = fields.Many2one(related='reverse_id.company_id', store=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Group', domain="[('company_id', '=', company_id)]")
    price_tax = fields.Float(compute='_compute_tax_amount', string='Total Tax', readonly=True, store=True)

    def write(self, vals):
        if vals.get('quantity') == 0:
            raise Warning(_('Can’t save the blanket order, because quantity product is 0.'))
        res = super(Orderline, self).write(vals)
        if vals.get('quantity'):
            for record in self:
                record.remaining_quantity = vals.get('quantity')
        return res

    @api.onchange('sequence')
    def set_account_group(self):
        for res in self:
            res.analytic_tag_ids = res.reverse_id.analytic_tag_ids

    @api.depends('quantity', 'price_unit', 'tax_id')
    def _compute_tax_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price_tax = line.price_unit
            taxes = line.tax_id.compute_all(price_tax, line.reverse_id.company_id.currency_id, line.quantity, product=line.product_id, partner=line.reverse_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
            })

    @api.depends('product_id')
    def get_analytic_tag(self):
        for res in self:
            if res.reverse_id.analytic_tag_ids:
                res.analytic_tag_ids = res.reverse_id.analytic_tag_ids

    def unlink(self):
        blanket = self.reverse_id
        res = super(Orderline, self).unlink()
        blanket._reset_sequence()
        return res

    @api.onchange('sequence')
    def set_sequence_line(self):
        for rec in self:
            rec.reverse_id._reset_sequence()

    @api.model
    def create(self, vals):
        if vals.get('quantity') == 0:
            raise Warning(_('Can’t create the blanket order, because quantity product is 0.'))
        line = super(Orderline, self).create(vals)
        if not self.env.context.get("keep_line_sequence", False):
            line.reverse_id._reset_sequence()
        line.remaining_quantity = line.quantity
        return line

    @api.constrains('delivered_qty','remaining_quantity','qty_invoiced')
    def _set_qty_bo_line(self):
        for res in self:
            res.reverse_id._set_qty_bo()

class ApprovalMatrixSaleOrderLines(models.Model):
    _inherit = 'approval.matrix.sale.order.lines'

    bo_order_id = fields.Many2one('saleblanket.saleblanket', string="Sale Order")

class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, vals):
        if vals.get('model') and \
            vals.get('model') == 'saleblanket.saleblanket' and vals.get('tracking_value_ids'):
            fields_to_hide = ['state1', 'state2', 'state3', 'bo_state', 'bo_state_1', 'delivery_status']

            state1 = self.env['ir.model.fields']._get('saleblanket.saleblanket', 'state1').id
            state2 = self.env['ir.model.fields']._get('saleblanket.saleblanket', 'state2').id
            state3 = self.env['ir.model.fields']._get('saleblanket.saleblanket', 'state3').id
            bo_state = self.env['ir.model.fields']._get('saleblanket.saleblanket', 'bo_state').id
            bo_state_1 = self.env['ir.model.fields']._get('saleblanket.saleblanket', 'bo_state_1').id
            delivery_status = self.env['ir.model.fields']._get('saleblanket.saleblanket', 'delivery_status').id
            is_approve_button = self.env['ir.model.fields']._get('saleblanket.saleblanket', 'is_approve_button').id
            approval_matrix_line_id = self.env['ir.model.fields']._get('saleblanket.saleblanket', 'approval_matrix_line_id').id
            write_date = self.env['ir.model.fields']._get('saleblanket.saleblanket', 'write_date').id
            write_uid = self.env['ir.model.fields']._get('saleblanket.saleblanket', 'write_uid').id
            vals['tracking_value_ids'] = [rec for rec in vals.get('tracking_value_ids') if
                                        rec[2].get('field') not in
                                        (state1, state2, state3,
                                        bo_state, bo_state_1, delivery_status,
                                        is_approve_button,approval_matrix_line_id,write_date,write_uid)]
        return super(MailMessage, self).create(vals)
