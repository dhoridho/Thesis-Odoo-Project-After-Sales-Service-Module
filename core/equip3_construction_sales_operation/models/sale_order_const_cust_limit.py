from odoo import api , fields , models, _
# from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from odoo.exceptions import AccessError, UserError, ValidationError


class SaleOrderConstInherit(models.Model):
    _inherit = 'sale.order.const'

    partner_credit_conform = fields.Boolean("Confirm Partner Order on Credit")
    approving_matrix_limit_id = fields.Many2many('limit.approval.matrix', string="Over Limit Approval Matrix")
    approved_matrix_limit_ids = fields.One2many('limit.approval.matrix.lines', 'order_const_id', store=True, string="Approved Matrix", compute='_compute_limit_matrix_lines')
    is_over_limit_validation = fields.Boolean(string="Over Limit Matrix", compute='_compute_is_over_limit_validation', store=False)
    is_limit_matrix_filled = fields.Boolean(string="Over Limit Matrix filled", store=False, compute='_compute_limit_matrix_filled')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('waiting_for_over_limit_approval', 'Waiting For Over Limit Approval'),
        ('over_limit_approved', 'Over Limit Approved'),
        ('to_approve', 'Waiting For Contract Approval'),
        ('quotation_approved', 'Quotation Approved'),
        ('reject', 'Quotation Rejected'),
        ('over_limit_reject', 'Over Limit Rejected'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('on_hold', 'On Hold'),
        ('block', 'Blocked')
        ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    is_direct_confirm = fields.Boolean(copy=False)
    limit_approval_matrix_line_id = fields.Many2one('limit.approval.matrix.lines', string='Over Limit Approval Matrix Line', compute='_get_approve_button_limit', store=False)
    is_approve_button_limit = fields.Boolean(string='Is Approve Button', compute='_get_approve_button_limit', store=False)
    limit_matrix_state_const = fields.Selection(related='state', tracking=False)
    limit_matrix_state_1_const = fields.Selection(related='state', tracking=False)
    limit_matrix_state_2_const = fields.Selection(related='state', tracking=False)
    sale_limit_state_const = fields.Selection(related='state', tracking=False)
    sale_limit_state_1_const = fields.Selection(related='state', tracking=False)
    sale_limit_state_2_const = fields.Selection(related='state', tracking=False)
    sale_limit_state_3_const = fields.Selection(related='state', tracking=False)
    sale_limit_state_4_const = fields.Selection(related='state', tracking=False)
    sale_limit_state_5_const = fields.Selection(related='state', tracking=False)
    approval_matrix_state_2_const = fields.Selection(related='state', tracking=False)
    approval_matrix_state_3_const = fields.Selection(related='state', tracking=False)
    approval_matrix_state_4_const = fields.Selection(related='state', tracking=False)
    approval_matrix_state_5_const = fields.Selection(related='state', tracking=False)
    approval_matrix_state_6_const = fields.Selection(related='state', tracking=False)
    approval_matrix_state_7_const = fields.Selection(related='state', tracking=False)
    approval_matrix_state_8_const = fields.Selection(related='state', tracking=False)
    state_cancel_1 = fields.Selection(related='state', tracking=False)
    state_cancel_2 = fields.Selection(related='state', tracking=False)

    def action_set_quotation(self):
        res = super(SaleOrderConstInherit, self).action_set_quotation()
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

    # @api.depends('state')
    # def _compute_is_print_report(self):
    #     res = super(SaleOrderConstInherit, self)._compute_is_print_report()
    #     for rec in self:
    #         if rec.state == 'waiting_for_over_limit_approval' and rec.is_over_limit_validation and not rec.is_customer_approval_matrix_const:
    #             rec.is_print_report = True
    #     return res

    def _get_approve_button_limit(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_limit_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
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
        is_over_limit_validation = IrConfigParam.get_param('is_over_limit_validation')
        for record in self:
            record.is_over_limit_validation = is_over_limit_validation

    @api.depends('approving_matrix_limit_id', 'state')
    def _compute_limit_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.state == 'waiting_for_over_limit_approval' and record.is_over_limit_validation:
                record.approved_matrix_limit_ids = []
                counter = 1
                record.approved_matrix_limit_ids = []
                for rec in record.approving_matrix_limit_id: 
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
                action_id = self.env.ref('equip3_construction_sales_operation.quotation_const_action')
                template_id = self.env.ref('equip3_construction_sales_operation.email_template_internal_sale_other_order_approval_const')
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order.const'
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
                        template_id.with_context(ctx).send_mail(record.id, True)
                else:
                    approver = record.approved_matrix_limit_ids[0].user_name_ids[0]
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.partner_id.email,
                        'approver_name' : approver.name,
                        'date': date.today(),
                        'url' : url,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)


    def action_confirm_approving_limit_matrix(self):
        for record in self:
            user = self.env.user
            action_id = self.env.ref('equip3_construction_sales_operation.quotation_const_action')
            template_id = self.env.ref('equip3_construction_sales_operation.email_template_reminder_for_sale_order_other_approval_const')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order.const'
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
                        limit_approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True})
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
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
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
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
            if len(record.approved_matrix_limit_ids) == len(record.approved_matrix_limit_ids.filtered(lambda r:r.approved)):
                record.write({'state': 'over_limit_approved'})
                if record.is_customer_approval_matrix_const:
                    if self.adjustment_sub == 0 and self.contract_amount1 > 0:
                        raise ValidationError(_("You haven't set Adjustment (Mark Up) for this contract"))
                    
                    if self.retention1 > 0 and not self.retention_term_1:
                        raise ValidationError(_("You haven't set Retention 1 Term for this contract"))
                    
                    if self.retention2 > 0 and not self.retention_term_2:
                        raise ValidationError(_("You haven't set Retention 2 Term for this contract"))
                    
                    if self.use_dp == True and self.down_payment == 0:
                        return {
                            'type': 'ir.actions.act_window',
                            'name': 'Confirmation',
                            'res_model': 'confirm.downpayment',
                            'view_type': 'form',
                            'view_mode': 'form',
                            'target': 'new',
                            }
                    
                    elif self.use_retention == True and self.retention1 == 0:
                        return {
                                'type': 'ir.actions.act_window',
                                'name': 'Confirmation',
                                'res_model': 'confirm.retention',
                                'view_type': 'form',
                                'view_mode': 'form',
                                'target': 'new',
                            }
                    else:
                        record.action_request_for_approval_limit()
                else:
                    record._button_confirm_contd()


    def action_reject_limit_approving_matrix(self):
        for record in self:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Reject Limit Reason',
                    'res_model': 'limit.approval.matrix.sale.reject.const',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }

    def send_credit_limit_email_alerts_notification(self):
        dbl_email = self.env.company.sale_credit_limit_email_alerts
        context = dict(self.env.context) or {}
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id='+ str(self.id) + '&view_type=form&model=sale.order.const'
        context.update({'url' : url})
        template = False
        if context.get('send_credit_limit'):
            template = self.env.ref(
                'equip3_construction_sales_operation.email_template_credit_limit_const')
        elif context.get('send_invoice_overdue'):
            template = self.env.ref(
                'equip3_construction_sales_operation.email_template_invoice_overdue_const')
        elif context.get('send_credit_invoice_overdue'):
            template = self.env.ref(
                'equip3_construction_sales_operation.email_template_credit_limit_invoice_overdue_const')


        if dbl_email:
            send_email_to = ''
            users_ids = []
            grp_id = self.env.ref(
                'equip3_construction_sales_operation.sh_group_sale_order_partner_credit_limit_const').id
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
            mail_message_ids = self.env['mail.message'].search([('model', '=', 'sale.order.const'), ('res_id', '=', self.id), ('message_type', '=', 'email')])
            mail_message_ids.sudo().write({'res_id': 0})

    def order_confirm(self):
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

        self.with_context(context)._button_confirm_contd()
        return True

    def _get_forbidden_state_confirm(self):
        return {'done', 'cancel'}

    def _prepare_confirmation_values(self):
        return {
            'state': 'sale',
        }
    
    def action_confirm(self):
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

        self.with_context(context)._button_confirm_contd()
        # self.create_contract_recurring_invoice()
        return True

    # def create_contract_recurring_invoice(self):
    #     for rec in self:
    #         create_analytic_account = self._context.get('analytic_account', False)
    #         if create_analytic_account:
    #             return rec
    #         if all(not i.product_id.subscription_product for i in self.order_line) and not (self.recurring_rule_type or self.recurring_interval):
    #             return rec

    #         for line in self.order_line:
    #             if line.product_id.subscription_product:
    #                 if line.product_id.recurring_interval and line.product_id.recurring_rule_type:
    #                     self.write({
    #                         'recurring_interval': line.product_id.recurring_interval,
    #                         'recurring_rule_type': line.product_id.recurring_rule_type
    #                     })

    #         if not self.recurring_interval and not self.recurring_rule_type:
    #             self.write({
    #                 'recurring_interval': 1,
    #                 'recurring_rule_type': 'monthly',
    #             })

    # #         if any(i.product_id.subscription_product for i in self.order_line) and not (self.recurring_rule_type and self.recurring_interval):
    # #             raise UserError(_('Please define a Recurring Period.'))
    #         #  exist_line = self.related_project_id.subscription_product_line_ids.filtered(lambda t: t.currency_id.id != self.pricelist_id.currency_id.id) #odoo11
    #         exist_line = self.analytic_account_id.subscription_product_line_ids.filtered(lambda t: t.currency_id.id != self.pricelist_id.currency_id.id)

    # #         if exist_line:
    # #             raise UserError(_('Currency of order is must be same as contract.'))
    #         #if not self.related_project_id:#odoo11
    #         if not self.analytic_account_id:
    #             #values = self._prepare_analytic_account_data()
    #             values = self._prepare_analytic_account_data(prefix=None)
    #             analytic_id = self.env['account.analytic.account'].create(values)
    #             # self.related_project_id = analytic_id.id #odoo11
    #             self.analytic_account_id = analytic_id.id
    #         analytic_account_ids = self.env['account.analytic.account'].search([])
    #         for line in self.order_line:
    #             if line.product_id.subscription_product:
    #               #  exist_line = self.related_project_id.subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id)#odoo11
    #                 exist_line = self.analytic_account_id.subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id)
    #                 if exist_line:
    #                     exist_line.product_uom_qty = exist_line.product_uom_qty + line.product_uom_qty
    #                     exist_line.price_subtotal = exist_line.price_unit * exist_line.product_uom_qty
    #                 else:
    #                     order_line={
    #                             #'subscription_product_line_id': self.related_project_id.id, #odoo11
    #                             'subscription_product_line_id': self.analytic_account_id.id,
    #                             'product_id':line.product_id.id,
    # #                            'layout_category_id':line.layout_category_id.id, odoo12
    #                             'name': line.name,
    #                             'product_uom_qty':line.product_uom_qty,
    #                             'product_uom':line.product_uom.id,
    #                             'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
    #                             'price_unit':line.price_unit,
    #                             'tax_ids':[(6, 0, line.tax_id.ids)],
    #                             'discount': line.discount,
    #                             'price_subtotal': line.price_subtotal,
    #                             'price_total':line.price_total,
    #                             'currency_id':self.pricelist_id.currency_id.id,
    #                         }
    #                     subscription = self.env['analytic.sale.order.const.line'].sudo().create(order_line)
    #             elif line.product_id:
    #                 exist_line = self.analytic_account_id.not_subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id)
    #                # exist_line = self.related_project_id.not_subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id) #odoo11
    #                 if exist_line:
    #                     exist_line.product_uom_qty = exist_line.product_uom_qty + line.product_uom_qty
    #                     exist_line.price_subtotal = exist_line.price_unit * exist_line.product_uom_qty
    #                 else:
    #                     order_line={
    #                            # 'not_subscription_product_line_id': self.related_project_id.id, #odoo11
    #                             'not_subscription_product_line_id': self.analytic_account_id.id,
    #                             'product_id':line.product_id.id,
    # #                            'layout_category_id':line.layout_category_id.id, odoo12
    #                             'name': line.name,
    #                             'product_uom_qty':line.product_uom_qty,
    #                             'product_uom':line.product_uom.id,
    #                             'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
    #                             'price_unit':line.price_unit,
    #                             'tax_ids':[(6, 0, line.tax_id.ids)],
    #                             'discount': line.discount,
    #                             'price_subtotal': line.price_subtotal,
    #                             'price_total':line.price_total,
    #                             'currency_id':self.pricelist_id.currency_id.id,
    #                         }
    #                     subscription = self.env['analytic.sale.order.const.line'].sudo().create(order_line)

    #         values = {
    #             'recurring_rule_type': self.recurring_rule_type,
    #             'recurring_interval': self.recurring_interval
    #         }
    #         today = date.today()
    #         periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
    #         invoicing_period = relativedelta(**{periods[values['recurring_rule_type']]: values['recurring_interval']})
    #         recurring_next_date = today + invoicing_period
    #         prevday = recurring_next_date - timedelta(days=1)
    #         if not self.analytic_account_id.recurring_next_date: # project_id
    #             self.analytic_account_id.update({
    #                             'end_date': prevday,
    #                             'recurring_next_date': recurring_next_date,
    #                             'recurring_rule_type': values['recurring_rule_type'],
    #                             'recurring_interval': values['recurring_interval'],
    #                         })
    #         if self.note:
    #             self.analytic_account_id.update({'terms_and_conditions': self.note})# project_id
    #         if not self.analytic_account_id.start_date:# project_id
    #             self.analytic_account_id.update({'start_date': fields.Date.today()})# project_id

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
                'fiscal_position_id': False,
            })
            return
        self = self.with_company(self.company_id)

        addr = self.partner_id.address_get(['invoice'])
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
        }
        user_id = partner_user.id
        if not self.env.context.get('not_self_saleperson'):
            user_id = user_id or self.env.uid

        if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms') and self.env.company.invoice_terms:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.company.invoice_terms
        warning_mess = {
            'message':'Selected Customer is set On Hold',
            'title':''
        }
        message_list = []
        is_warning = False
        if self.partner_id.customer_credit and self.partner_id.set_customer_onhold and self.partner_id.customer_credit_limit < 0:
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
            warning_message = warning_mess['message'] + ' and'.join(message_list)
            warning_mess['message'] = warning_message
            return {'warning': warning_mess, 'value': values}
        else:
            self.update(values)


    def action_confirm_approving_over_limit_matrix(self, state):
        context = dict(self.env.context) or {}
        if self.partner_id.set_customer_onhold and not self.partner_id.is_set_customer_on_hold and not self.partner_id.customer_on_hold_open_invoice:  # If Check
            tot_receivable = self.partner_id.credit + self.amount_total
            crdt_lmt = self.partner_id.customer_credit_limit
            if tot_receivable > crdt_lmt:
                if self.partner_credit_conform:  # Must Confirm Order at any condition
                    if state == 'sale':
                        self._button_confirm_contd()
                    else:
                        self.write({'state': state, 'is_direct_confirm': True})
                else:
                    context.update({'send_credit_limit' : True, 
                                    'show_credit_limit': False,
                                    'sale_id': self.id})
                    return {
                        'name': 'Customer Credit',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.const.partner.credit',
                        'view_id': self.env.ref('equip3_construction_sales_operation.sale_order_const_partner_credit_limit_form').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
            else:
                if state == 'sale':
                    self._button_confirm_contd()
                else:
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
                        'res_model': 'sale.order.const.partner.credit',
                        'view_id': self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_credit_limit').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
            else:
                if state == 'sale':
                    self._button_confirm_contd()
                else:
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
                    'res_model': 'sale.order.const.partner.credit',
                    'view_id': self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_open_invoice_limit').id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': context,
                }
            else:
                if state == 'sale':
                    self._button_confirm_contd()
                else:
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
                    view_id = self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_open_invoice_limit_and_overdue').id
                    name = 'Open Invoice Overlimit and Invoice Overdue'
                else:
                    view_id = self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_credit_limit').id
                    name = 'Invoice Overdue'
                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.const.partner.credit',
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
                        'res_model': 'sale.order.const.partner.credit',
                        'view_id': self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_open_invoice_limit').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
                else:
                    if state == 'sale':
                        self._button_confirm_contd()
                    else:
                        self.write({'state': state, 'is_direct_confirm': True})
        
        elif self.partner_id.customer_on_hold_open_invoice and self.partner_id.set_customer_onhold and not self.partner_id.is_set_customer_on_hold:
            tot_receivable = self.amount_total
            crdt_lmt = self.partner_id.customer_credit_limit
            credit_limit = False
            if tot_receivable > crdt_lmt:
                credit_limit = True
            if credit_limit:
                context.update({
                        'send_invoice_overdue' : False,
                        'customer_credit_limit': self.partner_id.customer_credit_limit,
                        'set_customer_onhold': self.partner_id.set_customer_onhold,
                        'avl_open_inv_limt': self.partner_id.avl_open_inv_limt,
                        'customer_on_hold_open_invoice': self.partner_id.customer_on_hold_open_invoice,
                        'sale_id': self.id,
                })
                if self.partner_id.avl_open_inv_limt <= 0:
                    view_id = self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_open_invoice_limit_and_credit_limit').id
                    name = 'Open Invoice Overlimit and Credit Overlimit'
                else:
                    context.update({
                        'show_credit_limit': False,
                    })
                    view_id = self.env.ref('equip3_construction_sales_operation.sale_order_const_partner_credit_limit_form').id
                    name = 'Customer Credit'
                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.const.partner.credit',
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
                        'res_model': 'sale.order.const.partner.credit',
                        'view_id': self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_open_invoice_limit').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
                else:
                    if state == 'sale':
                        self._button_confirm_contd()
                    else:
                        self.write({'state': state, 'is_direct_confirm': True})
        
        elif self.partner_id.is_set_customer_on_hold and self.partner_id.set_customer_onhold and self.partner_id.customer_on_hold_open_invoice:
            tot_receivable = self.amount_total
            crdt_lmt = self.partner_id.customer_credit_limit
            credit_limit = False
            if tot_receivable > crdt_lmt:
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
                    'customer_credit_limit': self.partner_id.customer_credit_limit,
                    'set_customer_onhold': self.partner_id.set_customer_onhold,
                    'invoice_number': ','.join(inv),
                    'send_invoice_overdue' : True,
                    'show_credit_limit': True,
                    'show_open_invoice_limit': True,
                    'sale_id': self.id
                })

                if self.partner_id.avl_open_inv_limt <= 0:
                    view_id = self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_open_invoice_limit_and_credit_limit_and_invoice_overdue').id
                    name = 'Open Invoice and Invoice Overdue and Credit Overlimit'
                else:
                    context.update({
                        'show_credit_invoice_limit': False,
                    })
                    view_id = self.env.ref('equip3_construction_sales_operation.sale_order_const_partner_credit_limit_form_view').id
                    name = 'Invoice Overdue and Credit Overlimit'
                return {
                        'name': name,
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.const.partner.credit',
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
                        'customer_credit_limit': self.partner_id.customer_credit_limit,
                        'set_customer_onhold': self.partner_id.set_customer_onhold,
                        'avl_open_inv_limt': self.partner_id.avl_open_inv_limt,
                        'customer_on_hold_open_invoice': self.partner_id.customer_on_hold_open_invoice,
                        'sale_id': self.id,
                })

                if self.partner_id.avl_open_inv_limt <= 0:
                    view_id = self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_open_invoice_limit_and_credit_limit').id
                    name = 'Open Invoice Overlimit and Credit Overlimit'
                else:
                    context.update({
                        'show_credit_limit': False,
                    })
                    view_id = self.env.ref('equip3_construction_sales_operation.sale_order_const_partner_credit_limit_form').id
                    name = 'Customer Credit'
                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.const.partner.credit',
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
                    view_id = self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_open_invoice_limit_and_overdue').id
                    name = 'Open Invoice Overlimit and Invoice Overdue'
                else:
                    view_id = self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_credit_limit').id
                    name = 'Invoice Overdue'

                return {
                    'name': name,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.const.partner.credit',
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
                        'res_model': 'sale.order.const.partner.credit',
                        'view_id': self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_open_invoice_limit').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
                else:
                    if state == 'sale':
                        self._button_confirm_contd()
                    else:
                        self.write({'state': state, 'is_direct_confirm': True})
        
        elif self.partner_id.is_set_customer_on_hold and self.partner_id.set_customer_onhold and not self.partner_id.customer_on_hold_open_invoice:
            tot_receivable = self.amount_total
            crdt_lmt = self.partner_id.customer_credit_limit
            credit_limit = False
            if tot_receivable > crdt_lmt:
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
                        'res_model': 'sale.order.const.partner.credit',
                        'view_id': self.env.ref('equip3_construction_sales_operation.sale_order_const_partner_credit_limit_form_view').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
            elif credit_limit:
                context.update({'send_credit_limit' : True, 'show_credit_limit': False, 'sale_id': self.id})
                return {
                        'name': 'Customer Credit',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.order.const.partner.credit',
                        'view_id': self.env.ref('equip3_construction_sales_operation.sale_order_const_partner_credit_limit_form').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
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
                        'res_model': 'sale.order.const.partner.credit',
                        'view_id': self.env.ref('equip3_construction_sales_operation.view_form_sale_order_const_partner_credit_limit').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
            else:
                if state == 'sale':
                    self._button_confirm_contd()
                else:
                    self.write({'state': state, 'is_direct_confirm': True})
        else:
            if state == 'sale':
                self._button_confirm_contd()
            else:
                self.write({'state': state, 'is_direct_confirm': True})

    def action_confirm_new(self):
        for rec in self:
            rec.button_confirm()
    
    def action_confirm_approving(self):
        if self.adjustment_sub == 0 and self.contract_amount1 > 0:
            raise ValidationError(_("You haven't set Adjustment (Mark Up) for this contract"))
        
        if self.retention1 > 0 and not self.retention_term_1:
            raise ValidationError(_("You haven't set Retention 1 Term for this contract"))
        
        if self.retention2 > 0 and not self.retention_term_2:
            raise ValidationError(_("You haven't set Retention 2 Term for this contract"))
        
        if self.use_dp == True and self.down_payment == 0:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Confirmation',
                'res_model': 'confirm.downpayment',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                }
        
        if self.use_retention == True and self.retention1 == 0:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmation',
                    'res_model': 'confirm.retention',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }
    
        if self.is_over_limit_validation == True:
            if not self.partner_id.is_set_customer_on_hold and \
                not self.partner_id.set_customer_onhold and \
                not self.partner_id.customer_on_hold_open_invoice:
                self.is_direct_confirm = True
            else:
                return self.action_confirm_approving_over_limit_matrix('quotation_approved')

    
    def action_request_for_approving(self):
        if len(self.sale_order_const_user_ids) == 0:
                raise ValidationError(
                    _("There's no contract approval matrix for this project with specific amount listed. You have to create it first."))

        if self.adjustment_sub == 0 and self.contract_amount1 > 0:
            raise ValidationError(_("You haven't set Adjustment (Mark Up) for this contract"))
        
        if self.retention1 > 0 and not self.retention_term_1:
            raise ValidationError(_("You haven't set Retention 1 Term for this contract"))
        
        if self.retention2 > 0 and not self.retention_term_2:
            raise ValidationError(_("You haven't set Retention 2 Term for this contract"))
        
        if self.use_dp == True and self.down_payment == 0:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Confirmation',
                'res_model': 'confirm.downpayment',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                }
        
        if self.use_retention == True and self.retention1 == 0:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmation',
                    'res_model': 'confirm.retention',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }
        
        if self.is_over_limit_validation == True:
            if not self.partner_id.is_set_customer_on_hold and \
                not self.partner_id.set_customer_onhold and \
                not self.partner_id.customer_on_hold_open_invoice:
                self.is_direct_confirm = True
                self.action_request_for_approving_sale_matrix()
            return self.action_confirm_approving_over_limit_matrix('to_approve')
        else:
            return self.action_request_for_approving_sale_matrix()

    def action_request_for_approving_limit(self):
        if self.adjustment_sub == 0 and self.contract_amount1 > 0:
            raise ValidationError(_("You haven't set Adjustment (Mark Up) for this contract"))
        
        if self.retention1 > 0 and not self.retention_term_1:
            raise ValidationError(_("You haven't set Retention 1 Term for this contract"))
        
        if self.retention2 > 0 and not self.retention_term_2:
            raise ValidationError(_("You haven't set Retention 2 Term for this contract"))
        
        if self.use_dp == True and self.down_payment == 0:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Confirmation',
                'res_model': 'confirm.downpayment',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                }
        
        if self.use_retention == True and self.retention1 == 0:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmation',
                    'res_model': 'confirm.retention',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }
        
        if self.is_over_limit_validation == True:
            if not self.partner_id.is_set_customer_on_hold and \
                not self.partner_id.set_customer_onhold and \
                not self.partner_id.customer_on_hold_open_invoice:
                self.is_direct_confirm = True
                self._button_confirm_contd()
            else:
                self.action_confirm_approving_over_limit_matrix('sale')


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, vals):
        if vals.get('model') and \
            vals.get('model') == 'sale.order.const' and vals.get('tracking_value_ids'):
            
            limit_matrix_state_const = self.env['ir.model.fields']._get('sale.order.const', 'limit_matrix_state_const').id
            limit_matrix_state_1_const = self.env['ir.model.fields']._get('sale.order.const', 'limit_matrix_state_1_const').id
            limit_matrix_state_2_const = self.env['ir.model.fields']._get('sale.order.const', 'limit_matrix_state_2_const').id
            sale_limit_state_const = self.env['ir.model.fields']._get('sale.order.const', 'sale_limit_state_const').id
            sale_limit_state_1_const = self.env['ir.model.fields']._get('sale.order.const', 'sale_limit_state_1_const').id
            sale_limit_state_2_const = self.env['ir.model.fields']._get('sale.order.const', 'sale_limit_state_2_const').id
            sale_limit_state_3_const = self.env['ir.model.fields']._get('sale.order.const', 'sale_limit_state_3_const').id
            sale_limit_state_4_const = self.env['ir.model.fields']._get('sale.order.const', 'sale_limit_state_4_const').id
            sale_limit_state_5_const = self.env['ir.model.fields']._get('sale.order.const', 'sale_limit_state_5_const').id
            approval_matrix_state_2_const = self.env['ir.model.fields']._get('sale.order.const', 'approval_matrix_state_2_const').id
            approval_matrix_state_3_const = self.env['ir.model.fields']._get('sale.order.const', 'approval_matrix_state_3_const').id
            approval_matrix_state_4_const = self.env['ir.model.fields']._get('sale.order.const', 'approval_matrix_state_4_const').id
            approval_matrix_state_5_const = self.env['ir.model.fields']._get('sale.order.const', 'approval_matrix_state_5_const').id
            approval_matrix_state_6_const = self.env['ir.model.fields']._get('sale.order.const', 'approval_matrix_state_6_const').id
            approval_matrix_state_7_const = self.env['ir.model.fields']._get('sale.order.const', 'approval_matrix_state_7_const').id
            vals['tracking_value_ids'] = [rec for rec in vals.get('tracking_value_ids') if 
                                        rec[2].get('field') not in 
                                        (limit_matrix_state_const, limit_matrix_state_1_const, limit_matrix_state_2_const, 
                                        sale_limit_state_const, sale_limit_state_1_const, sale_limit_state_2_const,
                                        sale_limit_state_3_const,sale_limit_state_4_const,sale_limit_state_5_const,
                                        approval_matrix_state_2_const,approval_matrix_state_3_const,approval_matrix_state_4_const,
                                        approval_matrix_state_5_const, approval_matrix_state_6_const, approval_matrix_state_7_const)]
        return super(MailMessage, self).create(vals)


class LimitApprovalMatrixLinesInherit(models.Model):
    _inherit = 'limit.approval.matrix.lines'

    order_const_id = fields.Many2one('sale.order.const', string="Sale Order")