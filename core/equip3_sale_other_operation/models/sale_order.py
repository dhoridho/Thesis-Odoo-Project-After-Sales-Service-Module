
from odoo import api , fields , models, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError, AccessError, UserError, RedirectWarning, Warning
import time



class SaleOrderPartnerCredit(models.TransientModel):
    _inherit = 'sale.order.partner.credit'

    sale_id = fields.Integer("ID Sale Order")

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderPartnerCredit, self).default_get(fields)
        if self._context.get('active_model', False) == 'saleblanket.saleblanket' and 'sale_id' in dict(self.env.context):
            sale_id = dict(self.env.context)['sale_id']
            sale_obj = self.env['sale.order'].search(
                [('id', '=', sale_id)], limit=1)
            if sale_obj:
                res = {}
                so_pend = ''
                inv_pend = ''
                ord_cnt = 0
                ord_amt = 0
                inv_cnt = 0
                inv_amt = 0
                res.update({'name': sale_obj.id})
                res.update({'current_order': sale_obj.amount_total})
                if sale_obj.partner_id:
                    res.update({'order_partner': sale_obj.partner_id.id, 'set_customer_onhold': sale_obj.partner_id.set_customer_onhold,
                    'total_receivable': sale_obj.partner_id.credit})
                    if not sale_obj.partner_id.set_customer_credit_limit_per_brand:
                        res.update({
                            'customer_credit_limit': sale_obj.partner_id.customer_credit_limit
                        })
                    else:
                        if sale_obj.brand and sale_obj.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == sale_obj.brand.id):
                            res.update({
                                'customer_credit_limit': sum(sale_obj.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == sale_obj.brand.id).mapped('customer_avail_credit_limit'))
                            })
                        else:
                            res.update({
                                'customer_credit_limit': 0.0
                            })

                so_pend_obj = self.env['sale.order'].search(
                    [('state', 'not in', ['done', 'cancel']), ('partner_id', '=', sale_obj.partner_id.id)])


                inv_pend_obj = self.env['account.move'].search([('move_type','=','out_invoice'),
                                                                ('payment_state','!=','paid'),('state','not in',['cancel']),('partner_id','=',sale_obj.partner_id.id )])


                for rec in so_pend_obj:
                    ord_cnt += 1
                    ord_amt += rec.amount_total
                if ord_cnt > 0:
                    so_pend = str(ord_cnt) + \
                              ' Sales Order(s) (Amt) : ' + str(ord_amt)
                    res.update({'sale_orders_cnt_amt': so_pend})
                for rec in inv_pend_obj:
                    inv_cnt += 1
                    inv_amt += rec.amount_total
                if inv_cnt > 0:
                    inv_pend = str(inv_cnt) + \
                               ' Invoice(s) (Amt) : ' + str(inv_amt)
                    res.update({'cust_invoice_cnt_amt': inv_pend})
        return res

    def onhold_sale_order(self):
        if self and self.name and self.order_partner:
            context = dict(self.env.context) or {}
            context.update({'invoice_number' : self.invoice_number})
            partner_obj = self.env['res.partner'].search(
                [('id', '=', self.order_partner.id)], limit=1)
            partner_obj.write(
                {'set_customer_onhold': self.set_customer_onhold})

            sale_obj = self.env['sale.order'].search([('id','=',self.name.id)])
            sale_obj.write({ 'state' : 'on_hold' })
            sale_obj.with_context(context).send_credit_limit_email_alerts_notification()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    approving_matrix_limit_id = fields.Many2many('limit.approval.matrix', string="Credit Limit Approval Matrix", copy=False)
    approved_matrix_limit_ids = fields.One2many('limit.approval.matrix.lines', 'order_id', store=True, string="Approved Matrix", compute='_compute_limit_matrix_lines')
    is_over_limit_validation = fields.Boolean(string="Over Limit Matrix", compute='_compute_is_over_limit_validation', store=False)
    is_limit_matrix_filled = fields.Boolean(string="Over Limit Matrix filled", store=False, compute='_compute_limit_matrix_filled')
    state = fields.Selection(selection_add=[
            ('waiting_for_over_limit_approval', 'Waiting For Over Limit Approval'),
            ('over_limit_approved', 'Over Limit Approved'),
            ('waiting_for_approval', 'Waiting For Sale Order Approval'),
            ('quotation_approved', 'Quotation Approved'),
            ('reject', 'Quotation Rejected'),
            ('revised', 'Order Revised'),
            ('over_limit_reject', 'Over Limit Rejected'),
            ('sent','Quotation Sent')
            ])
    is_direct_confirm = fields.Boolean(copy=False)
    limit_approval_matrix_line_id = fields.Many2one('limit.approval.matrix.lines', string='Over Limit Approval Matrix Line', compute='_get_approve_button_limit', store=False)
    is_approve_button_limit = fields.Boolean(string='Is Approve Button', compute='_get_approve_button_limit', store=False)
    limit_matrix_state = fields.Selection(related='state')
    limit_matrix_state_1 = fields.Selection(related='state')
    limit_matrix_state_2 = fields.Selection(related='state')
    sale_limit_state = fields.Selection(related='state')
    sale_limit_state_1 = fields.Selection(related='state')
    sale_limit_state_2 = fields.Selection(related='state')
    sale_limit_state_3 = fields.Selection(related='state')
    sale_limit_state_4 = fields.Selection(related='state')
    sale_limit_state_5 = fields.Selection(related='state')
    approval_matrix_state_2 = fields.Selection(related='state')
    approval_matrix_state_3 = fields.Selection(related='state')
    approval_matrix_state_4 = fields.Selection(related='state')
    approval_matrix_state_5 = fields.Selection(related='state')
    approval_matrix_state_6 = fields.Selection(related='state')
    approval_matrix_state_7 = fields.Selection(related='state')
    approval_matrix_state_8 = fields.Selection(related='state', tracking=False)
    approval_matrix_state_9 = fields.Selection(related='state', tracking=False)
    creditlim = fields.Boolean('creditlim', related='partner_id.customer_credit')
    hide_button_revise = fields.Boolean('Hide Revise', compute='_compute_hide_revise', store=True)
    is_credit_limit = fields.Boolean("Is Credit Limit", compute='_compute_is_credit_and_over_limit', store=True)
    is_over_limit = fields.Boolean("Is Over Limit", compute='_compute_is_credit_and_over_limit', store=True)
    cust_credit_limit = fields.Float("Customer Credit Limit")
    show_action_confirm = fields.Boolean("Show Action Confirm", compute='_compute_show_action_confirm', store=True)
    over_limit_approved = fields.Boolean("Over Limit Approved")
    show_customer_product_label = fields.Boolean('Show Customer Product Label Configuration', compute="_compute_show_customer_product_label", store=True)
    
    @api.depends('user_id')
    def _compute_show_customer_product_label(self):
        self.show_customer_product_label = self.env['ir.config_parameter'].sudo().get_param('show_customer_product_label', False)

    @api.onchange('partner_id','show_customer_product_label')
    def set_product_label(self):
        for rec in self:
            if rec.partner_id and rec.show_customer_product_label:
                for line in rec.order_line:
                    line._set_product_label()

    @api.depends('approving_matrix_sale_id','is_over_limit_validation','state','approval_matrix_state')
    def _compute_show_action_confirm(self):
        for rec in self:
            show_action_confirm = True
            if rec.is_over_limit:
                if rec.state != 'quotation_approved':
                    show_action_confirm = False
            if rec.is_customer_approval_matrix:
                if rec.state != 'quotation_approved':
                    show_action_confirm = False
            if not rec.is_over_limit and not rec.is_customer_approval_matrix:
                if rec.state not in ('draft','sent'):
                    show_action_confirm = False
            rec.show_action_confirm = show_action_confirm


    def action_confirm_approving_credit_limit(self):
        return {
            'name': 'Customer Credit',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.partner.credit',
            'view_id': self.env.ref('sh_sale_credit_limit.sale_order_partner_credit_limit_form').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self.env.context,
        }

    def action_confirm_approving_over_limit(self):
        context = dict(self.env.context) or {}
        for rec in self:
            over_limit = abs(rec.amount_total - rec.partner_id.customer_credit_limit)
            matrix_limit_id = self.env['limit.approval.matrix'].search([('minimum_amt', '<=', over_limit), ('maximum_amt', '>=', over_limit),
                                                                        ('config', '=', 'over_limit'), ('branch_id','=',rec.branch_id.id), ('company_id', '=', rec.company_id.id)], limit=1)
            is_send_mail = False
            if matrix_limit_id:
                is_send_mail = True
                rec.approving_matrix_limit_id = [(4, matrix_limit_id.id)]
                rec.write({'state': 'waiting_for_over_limit_approval'})
                if not rec.is_over_limit_validation:
                    rec.write({'state': 'over_limit_approved','partner_credit_conform': True})
                    rec.action_request_for_approval_limit()
            else:
                raise Warning(_("There is no approval matrix for this over limit amount"))
            if is_send_mail:
                rec.action_request_approval_overlimit_mail()

    @api.depends('partner_id','amount_total')
    def _compute_is_credit_and_over_limit(self):
        for rec in self:
            rec.is_credit_limit = False
            rec.is_over_limit = False
            if rec.state == 'on_hold' and self.user_has_groups('sh_sale_credit_limit.sh_group_sale_order_partner_credit_limit'):
                rec.is_credit_limit = False
                rec.is_over_limit = False
            elif rec and rec.partner_id:
                tot_receivable = rec.partner_id.credit + rec.amount_total
                crdt_lmt = rec.partner_id.customer_credit_limit
                if rec.partner_id.customer_credit:  # If Check
                    if tot_receivable > crdt_lmt:
                        if rec.partner_credit_conform:
                            rec.is_credit_limit = False
                        else:
                            rec.is_credit_limit = True
                if rec.partner_id.customer_over_limit:  # If Check
                    if tot_receivable > crdt_lmt:
                        rec.is_over_limit = True
                    else:
                        rec.is_over_limit = False

    @api.depends('approving_matrix_sale_id','approving_matrix_limit_id','state')
    def _compute_hide_revise(self):
        for rec in self:
            hide_button_revise = False
            if rec.state == 'draft':
                if rec.approving_matrix_sale_id or rec.approving_matrix_limit_id:
                    hide_button_revise = True
            elif rec.state == 'quotation_approved':
                if not rec.approved_matrix_ids:
                    hide_button_revise = True
            elif not rec.state in ('sent','cancel'):
                hide_button_revise = True
            rec.hide_button_revise = hide_button_revise

    def action_set_quotation(self):
        res = super(SaleOrder, self).action_set_quotation()
        for record in self:
            record.approved_matrix_limit_ids.write({
                'approved_users': False,
                'last_approved': False,
                'approved': False,
                'feedback': False,
                'time_stamp': False,
                'state_char': False,
            })
        return res

    @api.depends('state')
    def _compute_is_print_report(self):
        res = super(SaleOrder, self)._compute_is_print_report()
        for rec in self:
            if rec.state == 'waiting_for_over_limit_approval' and rec.is_over_limit_validation and not rec.is_customer_approval_matrix:
                rec.is_print_report = True
        return res

    def _get_approve_button_limit(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_limit_ids.filtered(lambda r: not r.approved and r.approver_state != 'refuse'), key=lambda r:r.sequence)
            if len(matrix_line) == 0:
                record.is_approve_button_limit = False
                record.limit_approval_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_name_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button_limit = True
                    record.limit_approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button_limit = False
                    record.limit_approval_matrix_line_id = False
            else:
                record.is_approve_button_limit = False
                record.limit_approval_matrix_line_id = False

    @api.depends('approving_matrix_limit_id')
    def _compute_limit_matrix_filled(self):
        for record in self:
            record.is_limit_matrix_filled = False
            if record.approving_matrix_limit_id:
                record.is_limit_matrix_filled = True

    @api.depends('partner_id')
    def _compute_is_over_limit_validation(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_over_limit_validation = IrConfigParam.get_param('is_over_limit_validation', False)
        for record in self:
            record.is_over_limit_validation = is_over_limit_validation

    @api.depends('approving_matrix_limit_id', 'state')
    def _compute_limit_matrix_lines(self):
        data = [(4, 0)]
        for record in self:
            if record.state == 'waiting_for_over_limit_approval' and record.is_over_limit_validation:
                # record.approved_matrix_limit_ids = []
                counter = len(record.approved_matrix_limit_ids) + 1
                # record.approved_matrix_limit_ids = []
                approving_matrix_limit_id = record.approving_matrix_limit_id
                if len(record.approving_matrix_limit_id) > 1:
                    approving_matrix_limit_id = record.approving_matrix_limit_id[-1]
                for rec in approving_matrix_limit_id:
                    for line in rec.approver_matrix_line_ids:
                        data.append((0, 0, {
                            'sequence' : counter,
                            'user_name_ids' : [(6, 0, line.user_name_ids.ids)],
                            'minimum_approver' : line.minimum_approver,
                            'approval_type': rec.config,
                        }))
                    counter += 1
                record.approved_matrix_limit_ids = data

    def action_request_approval_overlimit_mail(self):
        for record in self:
            if record.approved_matrix_limit_ids:
                action_id = self.env.ref('sale.action_quotations_with_onboarding')
                template_id = self.env.ref('equip3_sale_other_operation.email_template_internal_sale_other_order_approval')
                wa_template_id = self.env.ref('equip3_sale_other_operation.email_template_internal_sale_order_overlimit_wa')
                is_email_overlimit_approval = self.env['ir.config_parameter'].sudo().get_param('is_email_overlimit_approval', False)
                is_wa_overlimit_approval = self.env['ir.config_parameter'].sudo().get_param('is_wa_overlimit_approval', False)
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order'
                if record.approved_matrix_limit_ids and len(record.approved_matrix_limit_ids[0].user_name_ids) > 1:
                    for approved_matrix_id in record.approved_matrix_limit_ids[0].user_name_ids:
                        approver = approved_matrix_id
                        ctx = {
                            'email_from' : self.env.user.company_id.email,
                            'email_to' : approver.partner_id.email,
                            'approver_name' : approver.name,
                            'date': date.today(),
                            'url' : url,
                        }
                        if is_email_overlimit_approval:
                            template_id.with_context(ctx).send_mail(record.id, True)
                        if is_wa_overlimit_approval:
                            phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                            # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                            record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
                else:
                    approver = record.approved_matrix_limit_ids[0].user_name_ids[0]
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.partner_id.email,
                        'approver_name' : approver.name,
                        'date': date.today(),
                        'url' : url,
                    }
                    if is_email_overlimit_approval:
                        template_id.with_context(ctx).send_mail(record.id, True)
                    if is_wa_overlimit_approval:
                        phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                        # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                        record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)

    def action_confirm_approving_limit_matrix(self):
        context = dict(self.env.context) or {}
        for record in self:
            user = self.env.user
            is_email_overlimit_approval = self.env['ir.config_parameter'].sudo().get_param('is_email_overlimit_approval', False)
            is_wa_overlimit_approval = self.env['ir.config_parameter'].sudo().get_param('is_wa_overlimit_approval', False)
            action_id = self.env.ref('sale.action_quotations_with_onboarding')
            template_id = self.env.ref('equip3_sale_other_operation.email_template_reminder_for_sale_order_other_approval')
            approved_template_id = self.env.ref('equip3_sale_other_operation.email_template_sale_order_overlimit_approved')

            wa_template_id = self.env.ref('equip3_sale_other_operation.email_template_reminder_for_sale_order_overlimit_wa')
            wa_approved_template_id = self.env.ref('equip3_sale_other_operation.email_template_sale_order_overlimit_approved_wa')

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order'
            if record.is_approve_button_limit and record.limit_approval_matrix_line_id:
                limit_approval_matrix_line_id = record.limit_approval_matrix_line_id
                if user.id in limit_approval_matrix_line_id.user_name_ids.ids and \
                    user.id not in limit_approval_matrix_line_id.approved_users.ids:
                    name = limit_approval_matrix_line_id.state_char or ''
                    if name != '':
                        name += "\n • %s: Approved" % (self.env.user.name)
                    else:
                        name += "• %s: Approved" % (self.env.user.name)

                    limit_approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if limit_approval_matrix_line_id.minimum_approver == len(limit_approval_matrix_line_id.approved_users.ids):
                        limit_approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True, 'approver_state': 'approved'})
                        approver_name = ' and '.join(limit_approval_matrix_line_id.mapped('user_name_ids.name'))
                        next_approval_matrix_line_id = sorted(record.approved_matrix_limit_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_name_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_name_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : approving_matrix_line_user.partner_id.email,
                                    'approver_name' : approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter' : approver_name,
                                    'url' : url,
                                }
                                if is_email_overlimit_approval:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_wa_overlimit_approval:
                                    phone_num = str(approving_matrix_line_user.partner_id.mobile) or str(approving_matrix_line_user.partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, approving_matrix_line_user, phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id, approving_matrix_line_user, phone_num, url, submitter=approver_name)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_name_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : next_approval_matrix_line_id[0].user_name_ids[0].partner_id.email,
                                    'approver_name' : next_approval_matrix_line_id[0].user_name_ids[0].name,
                                    'date': date.today(),
                                    'submitter' : approver_name,
                                    'url' : url,
                                }
                                if is_email_overlimit_approval:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_wa_overlimit_approval:
                                    phone_num = str(next_approval_matrix_line_id[0].user_name_ids[0].partner_id.mobile) or str(next_approval_matrix_line_id[0].user_name_ids[0].partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, next_approval_matrix_line_id[0].user_name_ids[0], phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id, next_approval_matrix_line_id[0].user_name_ids[0], phone_num, url, submitter=approver_name)
                    else:
                        limit_approval_matrix_line_id.write({'approver_state': 'pending'})
            if len(record.approved_matrix_limit_ids.filtered(lambda r:r.approver_state != 'refuse')) == len(record.approved_matrix_limit_ids.filtered(lambda r:r.approved and r.approver_state != 'refuse')):
                record.write({
                    'state': 'over_limit_approved',
                    'partner_credit_conform': True,
                    'is_over_limit': False,
                    'over_limit_approved': True
                })
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.partner_id.email,
                    'date': date.today(),
                    'url' : url,
                }
                if is_email_overlimit_approval:
                    approved_template_id.sudo().with_context(ctx).send_mail(record.id, True)
                if is_wa_overlimit_approval:
                    phone_num = str(record.user_id.partner_id.mobile) or str(record.user_id.partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_approved_template_id, record.user_id.partner_id, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_approved_template_id, record.user_id.partner_id, phone_num, url)
                if record.is_customer_approval_matrix:
                    record.action_request_for_approval_limit()
                else:
                    record.order_confirm()



    def action_reject_limit_approving_matrix(self):
        for record in self:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Reject Limit Reason',
                    'res_model': 'limit.approval.matrix.sale.reject',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }

    def send_credit_limit_email_alerts_notification(self):
        dbl_email = self.env.company.sale_credit_limit_email_alerts
        context = dict(self.env.context) or {}
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id='+ str(self.id) + '&view_type=form&model=sale.order'
        context.update({'url' : url})
        template = False
        if context.get('send_credit_limit'):
            template = self.env.ref(
                'equip3_sale_other_operation.email_template_credit_limit')
        elif context.get('send_invoice_overdue'):
            template = self.env.ref(
                'equip3_sale_other_operation.email_template_invoice_overdue')
        elif context.get('send_credit_invoice_overdue'):
            template = self.env.ref(
                'equip3_sale_other_operation.email_template_credit_limit_invoice_overdue')


        if dbl_email:
            send_email_to = ''
            users_ids = []
            grp_id = self.env.ref(
                'sh_sale_credit_limit.sh_group_sale_order_partner_credit_limit').id
            if grp_id:
                res_grps = self.env['res.groups'].search(
                    [('id', '=', grp_id)], limit=1)
                if res_grps:
                    for rec in res_grps.users:
                        users_ids.append(rec.id)
            if dbl_email == 'all_approval':

                if template and users_ids:
                    res_users = self.env['res.users'].search(
                        [('id', 'in', users_ids)])

                    if res_users:
                        data = []
                        for record in res_users:
                            if record.email:
                                context.update({'user_name' : record.name})
                                template.with_context(context).send_mail(self.id, force_send=True, email_values={
                                                   'email_to': record.email})
                                data.append(record.name)
                        if data:
                            data_name = ",".join(data)
                            self.message_post(body=_("Email has been sent to %s for Sale Order on hold information") % data_name)

            elif dbl_email == 'by_team':
                if template and users_ids:
                    if self.team_id and self.team_id.member_ids:
                        data = []
                        for record in self.team_id.member_ids:
                            if (record.id in users_ids and record.email):
                                context.update({'user_name' : record.name})
                                template.with_context(context).send_mail(self.id, force_send=True, email_values={
                                                   'email_to': record.email})
                                data.append(record.name)
                        if data:
                            data_name = ",".join(data)
                            self.message_post(body=_("Email has been sent to %s for Sale Order on hold information") % data_name)

            elif dbl_email == 'specific_users':  # Must Send without checking any condition
                if template:
                    if self.env.company.sale_email_specific_user_id and self.env.company.sale_email_specific_user_id.email:
                        name = self.env.company.sale_email_specific_user_id.name
                        send_email_to = self.env.company.sale_email_specific_user_id.email
                        context.update({'user_name': name})
                        template.with_context(context).send_mail(self.id, force_send=True, email_values={
                                           'email_to': send_email_to})
                        self.message_post(body=_("Email has been sent to %s for Sale Order on hold information") % name)
            mail_message_ids = self.env['mail.message'].search([('model', '=', 'sale.order'), ('res_id', '=', self.id), ('message_type', '=', 'email')])
            mail_message_ids.sudo().write({'res_id': 0})

    def order_confirm(self):
        start = time.time()
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write(self._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        self.order_line.mapped("product_id").set_product_last_sales(self.id)
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()
        end = time.time()
        print("The time of execution of above program confirm is :",
              (end-start) * 10**3, "ms")
        return True

    def action_confirm(self):
        if self and self.partner_id and self.partner_id.customer_credit and not self.partner_credit_conform:  # If Check
            tot_receivable = self.partner_id.credit + self.amount_total
            crdt_lmt = self.partner_id.customer_credit_limit
            if tot_receivable > crdt_lmt:
                # raise Warning(_("The available credit limit for this customer is not sufficient to proceed the sales order"))
                return {
                    'name': 'Customer Credit',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.partner.credit',
                    'view_id': self.env.ref('equip3_sale_other_operation.sale_order_partner_over_limit_form').id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': self.env.context,
                }
        res = super().action_confirm()
        for rec in self:
            rec.create_contract_recurring_invoice()
            rec.order_line.mapped("product_id").set_product_last_sales(rec.id)
        return res

    def create_contract_recurring_invoice(self):
        for rec in self:
            create_analytic_account = self._context.get('analytic_account', False)
            if create_analytic_account:
                return rec
            if all(not i.product_id.subscription_product for i in self.order_line) and not (self.recurring_rule_type or self.recurring_interval):
                return rec

            for line in self.order_line:
                if line.product_id.subscription_product:
                    if line.product_id.recurring_interval and line.product_id.recurring_rule_type:
                        self.write({
                            'recurring_interval': line.product_id.recurring_interval,
                            'recurring_rule_type': line.product_id.recurring_rule_type
                        })

            if not self.recurring_interval and not self.recurring_rule_type:
                self.write({
                    'recurring_interval': 1,
                    'recurring_rule_type': 'monthly',
                })

    #         if any(i.product_id.subscription_product for i in self.order_line) and not (self.recurring_rule_type and self.recurring_interval):
    #             raise UserError(_('Please define a Recurring Period.'))
            #  exist_line = self.related_project_id.subscription_product_line_ids.filtered(lambda t: t.currency_id.id != self.pricelist_id.currency_id.id) #odoo11
            exist_line = self.analytic_account_id.subscription_product_line_ids.filtered(lambda t: t.currency_id.id != self.pricelist_id.currency_id.id)

    #         if exist_line:
    #             raise UserError(_('Currency of order is must be same as contract.'))
            #if not self.related_project_id:#odoo11
            if not self.analytic_account_id:
                #values = self._prepare_analytic_account_data()
                values = self._prepare_analytic_account_data(prefix=None)
                analytic_id = self.env['account.analytic.account'].create(values)
                # self.related_project_id = analytic_id.id #odoo11
                self.analytic_account_id = analytic_id.id
            analytic_account_ids = self.env['account.analytic.account'].search([])
            for line in self.order_line:
                if line.product_id.subscription_product:
                  #  exist_line = self.related_project_id.subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id)#odoo11
                    exist_line = self.analytic_account_id.subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id)
                    if exist_line:
                        exist_line.product_uom_qty = exist_line.product_uom_qty + line.product_uom_qty
                        exist_line.price_subtotal = exist_line.price_unit * exist_line.product_uom_qty
                    else:
                        order_line={
                                #'subscription_product_line_id': self.related_project_id.id, #odoo11
                    'subscription_product_line_id': self.analytic_account_id.id,
                                'product_id':line.product_id.id,
    #                            'layout_category_id':line.layout_category_id.id, odoo12
                                'name': line.name,
                                'product_uom_qty':line.product_uom_qty,
                                'product_uom':line.product_uom.id,
                                'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                                'price_unit':line.price_unit,
                                'tax_ids':[(6, 0, line.tax_id.ids)],
                                'discount': line.discount,
                                'price_subtotal': line.price_subtotal,
                                'price_total':line.price_total,
                                'currency_id':self.pricelist_id.currency_id.id,
                            }
                        subscription = self.env['analytic.sale.order.line'].sudo().create(order_line)
                elif line.product_id:
                    exist_line = self.analytic_account_id.not_subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id)
                   # exist_line = self.related_project_id.not_subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id) #odoo11
                    if exist_line:
                        exist_line.product_uom_qty = exist_line.product_uom_qty + line.product_uom_qty
                        exist_line.price_subtotal = exist_line.price_unit * exist_line.product_uom_qty
                    else:
                        order_line={
                               # 'not_subscription_product_line_id': self.related_project_id.id, #odoo11
                                'not_subscription_product_line_id': self.analytic_account_id.id,
                                'product_id':line.product_id.id,
    #                            'layout_category_id':line.layout_category_id.id, odoo12
                                'name': line.name,
                                'product_uom_qty':line.product_uom_qty,
                                'product_uom':line.product_uom.id,
                                'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                                'price_unit':line.price_unit,
                                'tax_ids':[(6, 0, line.tax_id.ids)],
                                'discount': line.discount,
                                'price_subtotal': line.price_subtotal,
                                'price_total':line.price_total,
                                'currency_id':self.pricelist_id.currency_id.id,
                            }
                        subscription = self.env['analytic.sale.order.line'].sudo().create(order_line)

            values = {
                'recurring_rule_type': self.recurring_rule_type,
                'recurring_interval': self.recurring_interval
            }
            today = date.today()
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            invoicing_period = relativedelta(**{periods[values['recurring_rule_type']]: values['recurring_interval']})
            recurring_next_date = today + invoicing_period
            prevday = recurring_next_date - timedelta(days=1)
            if not self.analytic_account_id.recurring_next_date: # project_id
                self.analytic_account_id.update({
                                'end_date': prevday,
                                'recurring_next_date': recurring_next_date,
                                'recurring_rule_type': values['recurring_rule_type'],
                                'recurring_interval': values['recurring_interval'],
                            })
            if self.note:
                self.analytic_account_id.update({'terms_and_conditions': self.note})# project_id
            if not self.analytic_account_id.start_date:# project_id
                self.analytic_account_id.update({'start_date': fields.Date.today()})# project_id

    def action_request_for_approval_limit(self):
        for record in self:
            if self.is_approval_matrix_filled:
                record.action_request_for_approving_sale_matrix()
            else:
                record.write({'state': 'quotation_approved'})

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'fiscal_position_id': False,
            })
            return
        self = self.with_company(self.company_id)

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        product_pricelist_id = self.env.company.product_pricelist_default.id
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or product_pricelist_id,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        user_id = partner_user.id
        if not self.env.context.get('not_self_saleperson'):
            user_id = user_id or self.env.uid
        if user_id and self.user_id.id != user_id:
            values['user_id'] = user_id

        if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms') and self.env.company.invoice_terms:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.company.invoice_terms
        if not self.env.context.get('not_self_saleperson') or not self.team_id:
            values['team_id'] = self.env['crm.team']._get_default_team_id(domain=['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)],user_id=user_id)
        warning_mess = {
            'message':'Selected Customer is set On Hold',
            'title':'Warning'
        }
        message_list = []
        is_warning = False
        customer_credit_limit = 0.0
        if not self.partner_id.set_customer_credit_limit_per_brand:
            customer_credit_limit = self.partner_id.customer_credit_limit
            cust_credit_limit = self.partner_id.cust_credit_limit
        elif self.brand and self.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == self.brand.id):
            customer_credit_limit = sum(self.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == self.brand.id).mapped('customer_avail_credit_limit'))
            cust_credit_limit = sum(self.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == self.brand.id).mapped('customer_credit_limit'))
        if self.partner_id.customer_credit and self.partner_id.set_customer_onhold and customer_credit_limit < 0:
            message_list.append(' due to its Credit Limit exceeds')
            is_warning = True
        if self.partner_id.is_customer_invoice_overdue and self.partner_id.is_set_customer_on_hold:
            max_days_overdue = self.partner_id.customer_max_invoice_overdue
            today = date.today()
            invoice_overdue = self.partner_id.invoice_ids.filtered(lambda i:i.invoice_date_due and (today-i.invoice_date_due).days > max_days_overdue)
            if invoice_overdue:
                message_list.append(' as there is an Invoice Overdue')
                is_warning = True
        if self.partner_id.is_open_invoice_limit and self.partner_id.customer_on_hold_open_invoice and self.partner_id.avl_open_inv_limt < 0:
            message_list.append(' due to Open Invoices limit exceeds')
            is_warning = True
        if is_warning:
            warning_message = ""
            if len(message_list) == 3:
                warning_message = "{},{}, and{}".format(message_list[0],message_list[1],message_list[2])
            else:
                warning_message = " and".join(message_list)
            warning_mess['message'] += warning_message
            return {'warning': warning_mess, 'value': values}
        else:
            self.update(values)


    def action_confirm_approving_over_limit_matrix(self, state):
        context = dict(self.env.context) or {}
        if self.partner_id.set_customer_onhold and not self.partner_id.is_set_customer_on_hold and not self.partner_id.customer_on_hold_open_invoice:  # If Check
            tot_receivable = self.partner_id.credit + self.amount_total
            crdt_lmt = 0.0
            is_crdt_lmt = False
            if not self.partner_id.set_customer_credit_limit_per_brand:
                crdt_lmt = self.partner_id.customer_credit_limit
                is_crdt_lmt = True
            elif self.brand and self.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == self.brand.id):
                crdt_lmt = sum(self.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == self.brand.id).mapped('customer_avail_credit_limit'))
                is_crdt_lmt = True
            if is_crdt_lmt and tot_receivable > crdt_lmt:
                if self.partner_credit_conform:  # Must Confirm Order at any condition
                    if state == 'sale':
                        self.order_confirm()
                    else:
                        if state == "waiting_for_approval":
                            self.action_request_for_approving_sale_matrix()
                        self.write({'state': state, 'is_direct_confirm': True})
                else:
                    # raise Warning(_("The available credit limit for this customer is not sufficient to proceed the sales order"))
                    return {
                        'name': 'Customer Credit',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.partner.credit',
                        'view_id': self.env.ref('equip3_sale_other_operation.sale_order_partner_over_limit_form').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': self.env.context,
                    }
            else:
                if state == 'sale':
                    self.order_confirm()
                else:
                    if state == "waiting_for_approval":
                        self.action_request_for_approving_sale_matrix()
                    self.write({'state': state, 'is_direct_confirm': True})
        elif self.partner_id.is_set_customer_on_hold and not self.partner_id.set_customer_onhold and not self.partner_id.customer_on_hold_open_invoice:
            default_max_days = self.partner_id.customer_max_invoice_overdue
            invoices = self.env['account.move'].search(
            [('partner_id', '=', self.partner_id.id), ('state', '=', 'posted'),('payment_state','in',('not_paid','in_payment','partial')),
                ('invoice_date_due', '<', datetime.now().date()), ('move_type', '=', 'out_invoice')])
            inv = []
            if invoices:
                today_date = datetime.now().date()
                for invoice in invoices:
                    deviation = today_date - invoice.invoice_date_due
                    if deviation.days > default_max_days:
                        inv.append(invoice.name + " : " + invoice.invoice_date_due.strftime('%d/%m/%Y'))
            if inv:
                context.update({
                    'customer_max_invoice_overdue': self.partner_id.customer_max_invoice_overdue,
                    'is_set_customer_on_hold': self.partner_id.is_set_customer_on_hold,
                    'invoice_number': ','.join(inv),
                    'send_invoice_overdue' : True,
                    'show_invoice_limit': False,
                    'sale_id': self.id
                })
                return {
                        'name': 'Invoice Overdue',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.partner.credit',
                        'view_id': self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_credit_limit').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
            else:
                if state == 'sale':
                    self.order_confirm()
                else:
                    if state == "waiting_for_approval":
                        self.action_request_for_approving_sale_matrix()
                    self.write({'state': state, 'is_direct_confirm': True})
        elif self.partner_id.customer_on_hold_open_invoice and self.partner_id.avl_open_inv_limt <= 0 and not self.partner_id.is_set_customer_on_hold and not self.partner_id.set_customer_onhold:
            context.update({
                    'send_invoice_overdue' : False,
                    'show_credit_limit': False,
                    'show_open_invoice_limit': True,
                    'avl_open_inv_limt': self.partner_id.avl_open_inv_limt,
                    'customer_on_hold_open_invoice': self.partner_id.customer_on_hold_open_invoice,
                    'sale_id': self.id,
            })
            if self.partner_id.avl_open_inv_limt <= 0:
                return {
                    'name': 'Open Invoice Overlimit',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.partner.credit',
                    'view_id': self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_open_invoice_limit').id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': context,
                }
            else:
                if state == 'sale':
                    self.order_confirm()
                else:
                    if state == "waiting_for_approval":
                        self.action_request_for_approving_sale_matrix()
                    self.write({'state': state, 'is_direct_confirm': True})
        elif self.partner_id.customer_on_hold_open_invoice and self.partner_id.is_set_customer_on_hold and not self.partner_id.set_customer_onhold:
            default_max_days = self.partner_id.customer_max_invoice_overdue
            invoices = self.env['account.move'].search(
            [('partner_id', '=', self.partner_id.id), ('state', '=', 'posted'),('payment_state','in',('not_paid','in_payment','partial')),
                ('invoice_date_due', '<', datetime.now().date()), ('move_type', '=', 'out_invoice')])
            inv = []
            if invoices:
                today_date = datetime.now().date()
                for invoice in invoices:
                    deviation = today_date - invoice.invoice_date_due
                    if deviation.days > default_max_days:
                        inv.append(invoice.name + " : " + invoice.invoice_date_due.strftime('%d/%m/%Y'))
            if inv:
                context.update({
                        'send_invoice_overdue' : True,
                        'show_credit_limit': False,
                        'show_open_invoice_limit': True,
                        'invoice_number': ','.join(inv),
                        'customer_max_invoice_overdue': self.partner_id.customer_max_invoice_overdue,
                        'is_set_customer_on_hold': self.partner_id.is_set_customer_on_hold,
                        'avl_open_inv_limt': self.partner_id.avl_open_inv_limt,
                        'customer_on_hold_open_invoice': self.partner_id.customer_on_hold_open_invoice,
                        'sale_id': self.id,
                })
                if self.partner_id.avl_open_inv_limt <= 0:
                    view_id = self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_open_invoice_limit_and_overdue').id
                    name = 'Open Invoice Overlimit and Invoice Overdue'
                else:
                    view_id = self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_credit_limit').id
                    name = 'Invoice Overdue'
                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.partner.credit',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': context,
                }
            else:
                if self.partner_id.avl_open_inv_limt <= 0:
                    context.update({
                            'send_invoice_overdue' : False,
                            'show_credit_limit': False,
                            'show_open_invoice_limit': True,
                            'avl_open_inv_limt': self.partner_id.avl_open_inv_limt,
                            'customer_on_hold_open_invoice': self.partner_id.customer_on_hold_open_invoice,
                            'sale_id': self.id,
                    })
                    return {
                        'name': 'Open Invoice Overlimit',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.partner.credit',
                        'view_id': self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_open_invoice_limit').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
                else:
                    if state == 'sale':
                        self.order_confirm()
                    else:
                        if state == "waiting_for_approval":
                            self.action_request_for_approving_sale_matrix()
                        self.write({'state': state, 'is_direct_confirm': True})
        elif self.partner_id.customer_on_hold_open_invoice and self.partner_id.set_customer_onhold and not self.partner_id.is_set_customer_on_hold:
            tot_receivable = self.amount_total
            crdt_lmt = 0.0
            is_crdt_lmt = False
            if not self.partner_id.set_customer_credit_limit_per_brand:
                crdt_lmt = self.partner_id.customer_credit_limit
                is_crdt_lmt = True
            elif self.brand and self.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == self.brand.id):
                crdt_lmt = sum(self.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == self.brand.id).mapped('customer_avail_credit_limit'))
                is_crdt_lmt = True
            credit_limit = False
            if tot_receivable > crdt_lmt and is_crdt_lmt:
                credit_limit = True
            if credit_limit:
                context.update({
                        'send_invoice_overdue' : False,
                        'customer_credit_limit': crdt_lmt,
                        'set_customer_onhold': self.partner_id.set_customer_onhold,
                        'avl_open_inv_limt': self.partner_id.avl_open_inv_limt,
                        'customer_on_hold_open_invoice': self.partner_id.customer_on_hold_open_invoice,
                        'sale_id': self.id,
                })
                if self.partner_id.avl_open_inv_limt <= 0:
                    view_id = self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_open_invoice_limit_and_credit_limit').id
                    name = 'Open Invoice Overlimit and Credit Overlimit'
                else:
                    context.update({
                        'show_credit_limit': False,
                    })
                    view_id = self.env.ref('sh_sale_credit_limit.sale_order_partner_credit_limit_form').id
                    name = 'Customer Credit'
                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.partner.credit',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': context,
                }
            else:
                if self.partner_id.avl_open_inv_limt <= 0:
                    context.update({
                            'send_invoice_overdue' : False,
                            'show_credit_limit': False,
                            'show_open_invoice_limit': True,
                            'avl_open_inv_limt': self.partner_id.avl_open_inv_limt,
                            'customer_on_hold_open_invoice': self.partner_id.customer_on_hold_open_invoice,
                            'sale_id': self.id,
                    })
                    return {
                        'name': 'Open Invoice Overlimit',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.partner.credit',
                        'view_id': self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_open_invoice_limit').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
                else:
                    if state == 'sale':
                        self.order_confirm()
                    else:
                        if state == "waiting_for_approval":
                            self.action_request_for_approving_sale_matrix()
                        self.write({'state': state, 'is_direct_confirm': True})
        elif self.partner_id.is_set_customer_on_hold and self.partner_id.set_customer_onhold and self.partner_id.customer_on_hold_open_invoice:
            tot_receivable = self.amount_total
            crdt_lmt = 0.0
            is_crdt_lmt = False
            if not self.partner_id.set_customer_credit_limit_per_brand:
                crdt_lmt = self.partner_id.customer_credit_limit
                is_crdt_lmt = True
            elif self.brand and self.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == self.brand.id):
                crdt_lmt = sum(self.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == self.brand.id).mapped('customer_avail_credit_limit'))
                is_crdt_lmt = True
            credit_limit = False
            if tot_receivable > crdt_lmt and is_crdt_lmt:
                credit_limit = True
            default_max_days = self.partner_id.customer_max_invoice_overdue
            invoices = self.env['account.move'].search(
            [('partner_id', '=', self.partner_id.id), ('state', '=', 'posted'),('payment_state','in',('not_paid','in_payment','partial')),('move_type', '=', 'out_invoice'),
                ('invoice_date_due', '<', datetime.now().date())])
            inv = []
            if invoices:
                today_date = datetime.now().date()
                for invoice in invoices:
                    deviation = today_date - invoice.invoice_date_due
                    if deviation.days > default_max_days:
                        inv.append(invoice.name + " : " + invoice.invoice_date_due.strftime('%d/%m/%Y'))
            if inv and credit_limit:
                context.update({
                    'customer_max_invoice_overdue': self.partner_id.customer_max_invoice_overdue,
                    'is_set_customer_on_hold': self.partner_id.is_set_customer_on_hold,
                    'avl_open_inv_limt': self.partner_id.avl_open_inv_limt,
                    'customer_on_hold_open_invoice': self.partner_id.customer_on_hold_open_invoice,
                    'customer_credit_limit': crdt_lmt,
                    'set_customer_onhold': self.partner_id.set_customer_onhold,
                    'invoice_number': ','.join(inv),
                    'send_invoice_overdue' : True,
                    'show_credit_limit': True,
                    'show_open_invoice_limit': True,
                    'sale_id': self.id
                })

                if self.partner_id.avl_open_inv_limt <= 0:
                    view_id = self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_open_invoice_limit_and_credit_limit_and_invoice_overdue').id
                    name = 'Open Invoice and Invoice Overdue and Credit Overlimit'
                else:
                    context.update({
                        'show_credit_invoice_limit': False,
                    })
                    view_id = self.env.ref('equip3_sale_other_operation.sale_order_partner_credit_limit_form_view').id
                    name = 'Invoice Overdue and Credit Overlimit'
                return {
                        'name': name,
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.partner.credit',
                        'view_id': view_id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
            elif credit_limit:
                context.update({
                        'send_invoice_overdue' : False,
                        'show_credit_limit': True,
                        'show_open_invoice_limit': True,
                        'customer_credit_limit': crdt_lmt,
                        'set_customer_onhold': self.partner_id.set_customer_onhold,
                        'avl_open_inv_limt': self.partner_id.avl_open_inv_limt,
                        'customer_on_hold_open_invoice': self.partner_id.customer_on_hold_open_invoice,
                        'sale_id': self.id,
                })

                if self.partner_id.avl_open_inv_limt <= 0:
                    view_id = self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_open_invoice_limit_and_credit_limit').id
                    name = 'Open Invoice Overlimit and Credit Overlimit'
                else:
                    context.update({
                        'show_credit_limit': False,
                    })
                    view_id = self.env.ref('sh_sale_credit_limit.sale_order_partner_credit_limit_form').id
                    name = 'Customer Credit'
                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.partner.credit',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': context,
                }
            elif inv:
                context.update({
                        'send_invoice_overdue' : True,
                        'show_credit_limit': False,
                        'show_open_invoice_limit': True,
                        'invoice_number': ','.join(inv),
                        'customer_max_invoice_overdue': self.partner_id.customer_max_invoice_overdue,
                        'is_set_customer_on_hold': self.partner_id.is_set_customer_on_hold,
                        'avl_open_inv_limt': self.partner_id.avl_open_inv_limt,
                        'customer_on_hold_open_invoice': self.partner_id.customer_on_hold_open_invoice,
                        'sale_id': self.id,
                })

                if self.partner_id.avl_open_inv_limt <= 0:
                    view_id = self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_open_invoice_limit_and_overdue').id
                    name = 'Open Invoice Overlimit and Invoice Overdue'
                else:
                    view_id = self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_credit_limit').id
                    name = 'Invoice Overdue'

                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.partner.credit',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': context,
                }
            else:
                if self.partner_id.avl_open_inv_limt <= 0:
                    context.update({
                            'send_invoice_overdue' : False,
                            'show_credit_limit': False,
                            'show_open_invoice_limit': True,
                            'avl_open_inv_limt': self.partner_id.avl_open_inv_limt,
                            'customer_on_hold_open_invoice': self.partner_id.customer_on_hold_open_invoice,
                            'sale_id': self.id,
                    })
                    return {
                        'name': 'Open Invoice Overlimit',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.partner.credit',
                        'view_id': self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_open_invoice_limit').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
                else:
                    if state == 'sale':
                        self.order_confirm()
                    else:
                        if state == "waiting_for_approval":
                            self.action_request_for_approving_sale_matrix()
                        self.write({'state': state, 'is_direct_confirm': True})
        elif self.partner_id.is_set_customer_on_hold and self.partner_id.set_customer_onhold and not self.partner_id.customer_on_hold_open_invoice:
            tot_receivable = self.amount_total
            crdt_lmt = 0.0
            is_crdt_lmt = False
            if not self.partner_id.set_customer_credit_limit_per_brand:
                crdt_lmt = self.partner_id.customer_credit_limit
                is_crdt_lmt = True
            elif self.brand and self.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == self.brand.id):
                crdt_lmt = sum(self.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == self.brand.id).mapped('customer_avail_credit_limit'))
                is_crdt_lmt = True
            credit_limit = False
            if tot_receivable > crdt_lmt and is_crdt_lmt:
                credit_limit = True
            default_max_days = self.partner_id.customer_max_invoice_overdue
            invoices = self.env['account.move'].search(
            [('partner_id', '=', self.partner_id.id), ('state', '=', 'posted'),('payment_state','in',('not_paid','in_payment','partial')),('move_type', '=', 'out_invoice'),
                ('invoice_date_due', '<', datetime.now().date())])
            inv = []
            if invoices:
                today_date = datetime.now().date()
                for invoice in invoices:
                    deviation = today_date - invoice.invoice_date_due
                    if deviation.days > default_max_days:
                        inv.append(invoice.name + " : " + invoice.invoice_date_due.strftime('%d/%m/%Y'))
            if inv and credit_limit:
                context.update({
                    'customer_max_invoice_overdue': self.partner_id.customer_max_invoice_overdue,
                    'is_set_customer_on_hold': self.partner_id.is_set_customer_on_hold,
                    'invoice_number': ','.join(inv),
                    'send_credit_invoice_overdue' : True,
                    'show_credit_invoice_limit': False,
                    'sale_id': self.id
                })
                return {
                        'name': 'Customer Credit Limit and Invoice Overdue',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.partner.credit',
                        'view_id': self.env.ref('equip3_sale_other_operation.sale_order_partner_credit_limit_form_view').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
            elif credit_limit:
                context.update({'send_credit_limit' : True, 'show_credit_limit': False, 'sale_id': self.id})
                if not self.partner_credit_conform:
                    # raise Warning(_("The available credit limit for this customer is not sufficient to proceed the sales order"))
                    return {
                        'name': 'Customer Credit',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.partner.credit',
                        'view_id': self.env.ref('equip3_sale_other_operation.sale_order_partner_over_limit_form').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': self.env.context,
                    }
            elif inv:
                context = dict(self.env.context) or {}
                context.update({
                    'customer_max_invoice_overdue': self.partner_id.customer_max_invoice_overdue,
                    'is_set_customer_on_hold': self.partner_id.is_set_customer_on_hold,
                    'invoice_number': ','.join(inv),
                    'send_invoice_overdue' : True,
                    'show_invoice_limit': False,
                    'sale_id': self.id
                })
                return {
                        'name': 'Invoice Overdue',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.partner.credit',
                        'view_id': self.env.ref('equip3_sale_other_operation.view_form_sale_order_partner_credit_limit').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
            else:
                if state == 'sale':
                    self.order_confirm()
                else:
                    if state == "waiting_for_approval":
                        self.action_request_for_approving_sale_matrix()
                    self.write({'state': state, 'is_direct_confirm': True})
        else:
            if state == 'sale':
                self.order_confirm()
            else:
                if state == "waiting_for_approval":
                    self.action_request_for_approving_sale_matrix()
                self.write({'state': state, 'is_direct_confirm': True})

    def action_confirm_approving(self):
        if not self.partner_id.is_set_customer_on_hold and \
            not self.partner_id.set_customer_onhold and \
            not self.partner_id.customer_on_hold_open_invoice:
            self.is_direct_confirm = True
        return self.action_confirm_approving_over_limit_matrix('quotation_approved')

    def action_request_for_approving(self):
        if not self.approving_matrix_sale_id:
            raise ValidationError(_("You don’t have approval matrix for this quotation, please set Sales Approval Matrix"))
        if self and self.partner_id and self.partner_id.customer_credit and not self.partner_credit_conform:  # If Check
            tot_receivable = self.partner_id.credit + self.amount_total
            crdt_lmt = self.partner_id.customer_credit_limit
            if tot_receivable > crdt_lmt:
                # raise Warning(_("The available credit limit for this customer is not sufficient to proceed the sales order"))
                return {
                    'name': 'Customer Credit',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.partner.credit',
                    'view_id': self.env.ref('equip3_sale_other_operation.sale_order_partner_over_limit_form').id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': self.env.context,
                }
        if not self.partner_id.is_set_customer_on_hold and \
            not self.partner_id.set_customer_onhold and \
            not self.partner_id.customer_on_hold_open_invoice:
            self.is_direct_confirm = True
            # self.action_request_for_approving_sale_matrix()
        return self.action_confirm_approving_over_limit_matrix('waiting_for_approval')

    def action_request_for_approving_limit(self):
        if not self.partner_id.is_set_customer_on_hold and \
            not self.partner_id.set_customer_onhold and \
            not self.partner_id.customer_on_hold_open_invoice:
            self.is_direct_confirm = True
            return self.order_confirm()
        else:
            return self.action_confirm_approving_over_limit_matrix('sale')

class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, vals):
        if vals.get('model') and \
            vals.get('model') == 'sale.order' and vals.get('tracking_value_ids'):

            limit_matrix_state = self.env['ir.model.fields']._get('sale.order', 'limit_matrix_state').id
            limit_matrix_state_1 = self.env['ir.model.fields']._get('sale.order', 'limit_matrix_state_1').id
            limit_matrix_state_2 = self.env['ir.model.fields']._get('sale.order', 'limit_matrix_state_2').id
            sale_limit_state = self.env['ir.model.fields']._get('sale.order', 'sale_limit_state').id
            sale_limit_state_1 = self.env['ir.model.fields']._get('sale.order', 'sale_limit_state_1').id
            sale_limit_state_2 = self.env['ir.model.fields']._get('sale.order', 'sale_limit_state_2').id
            sale_limit_state_3 = self.env['ir.model.fields']._get('sale.order', 'sale_limit_state_3').id
            sale_limit_state_4 = self.env['ir.model.fields']._get('sale.order', 'sale_limit_state_4').id
            sale_limit_state_5 = self.env['ir.model.fields']._get('sale.order', 'sale_limit_state_5').id
            approval_matrix_state_2 = self.env['ir.model.fields']._get('sale.order', 'approval_matrix_state_2').id
            approval_matrix_state_3 = self.env['ir.model.fields']._get('sale.order', 'approval_matrix_state_3').id
            approval_matrix_state_4 = self.env['ir.model.fields']._get('sale.order', 'approval_matrix_state_4').id
            approval_matrix_state_5 = self.env['ir.model.fields']._get('sale.order', 'approval_matrix_state_5').id
            approval_matrix_state_6 = self.env['ir.model.fields']._get('sale.order', 'approval_matrix_state_6').id
            approval_matrix_state_7 = self.env['ir.model.fields']._get('sale.order', 'approval_matrix_state_7').id
            vals['tracking_value_ids'] = [rec for rec in vals.get('tracking_value_ids') if
                                        rec[2].get('field') not in
                                        (limit_matrix_state, limit_matrix_state_1, limit_matrix_state_2,
                                        sale_limit_state, sale_limit_state_1, sale_limit_state_2,
                                        sale_limit_state_3,sale_limit_state_4,sale_limit_state_5,
                                        approval_matrix_state_2,approval_matrix_state_3,approval_matrix_state_4,
                                        approval_matrix_state_5, approval_matrix_state_6, approval_matrix_state_7)]
        return super(MailMessage, self).create(vals)

    # def set_product_template_last_sale(self, date_order, price_unit, partner_id):
    #     self._cr.execute("""UPDATE product_template SET last_sales_date=%s,last_sales_price=%s,last_customer_id=%s WHERE id = %s""",(str(date_order),price_unit,partner_id,self.id))
    #     self._cr.commit()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_label = fields.Char("Customer Products Label", compute='', store=True)

    @api.onchange('product_template_id','product_id','order_id.partner_id','order_id.show_customer_product_label')
    def _set_product_label(self):
        for rec in self:
            if rec.order_id.show_customer_product_label and rec.product_id:
                self.env.cr.execute("""
                    SELECT product_label
                    FROM customer_product_template_line
                    WHERE res_customer_id = %s and product_id = %s ORDER BY id DESC LIMIT 1
                """ % (rec.order_id.partner_id.id,rec.product_id.id))
                product_label = self.env.cr.fetchall()
                rec.product_label = product_label[0][0] if product_label else ""
            else:
                rec.product_label = ""