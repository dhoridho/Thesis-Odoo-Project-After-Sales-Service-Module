from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json
import pandas as pd
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import calendar
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class MonthlyPurchaseBudget(models.Model):
    _name = "monthly.purchase.budget"
    _description = "Monthly Purchase Budget"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']


    name = fields.Char(string="Number", required=True)
    budget_purchase_id = fields.Many2one('budget.purchase', string="Purchase Budget")
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    account_tag_ids_domain = fields.Char(string='Analytic Group Domain', compute='_compute_account_tag_ids_domain')
    month_period_id = fields.Many2one('month.period', 'Month')
    month_period_id_domain = fields.Char(string='Month Domain', compute='_compute_month_period_id_domain')
    total_planned_amount = fields.Float(string="Total Budget", related="budget_purchase_id.total_planned_amount")
    total_avail_amount = fields.Float(string="Available Budget", related="budget_purchase_id.total_avail_amount")
    company_id = fields.Many2one('res.company', string="Company", related="budget_purchase_id.company_id")
    branch_id = fields.Many2one('res.branch', string="Branch", related="budget_purchase_id.branch_id")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting for Approval'),
        ('confirm', 'Confirm'),         
        ('validate', 'Validate'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
        ('rejected', 'Rejected'),
    ], 'Status', default='draft', index=True, required=True, copy=False, tracking=True)
    monthly_purchase_budget_line_ids = fields.One2many('monthly.purchase.budget.line', 'monthly_purchase_budget_id', 'Monthly Purchase Budget Line')
    currency_id = fields.Many2one('res.currency', related='budget_purchase_id.currency_id', readonly=True)
    total_line_planned_amount = fields.Monetary(string="Planned Amount", compute='_compute_amount', currency_field="currency_id", store=True)
    total_line_practical_amount = fields.Monetary(string="Used Amount", compute='_compute_amount', currency_field="currency_id", store=True)
    total_line_remaining_amount = fields.Monetary(string="Remaining Amount", compute='_compute_amount', currency_field="currency_id", store=True)
    total_line_avail_amount = fields.Monetary(string="Avail Amount", compute='_compute_amount', currency_field="currency_id")
    total_line_reserve_amount = fields.Monetary(string="Reserve Amount", compute='_compute_amount', currency_field="currency_id")
    date_from = fields.Date('Start Date', compute='_compute_date', store=True)
    date_to = fields.Date('End Date', compute='_compute_date', store=True)
    is_allowed_to_approval_matrix = fields.Boolean(string="Is Allowed Approval Matrix", compute='_get_approve_status_from_config')
    approval_matrix = fields.Many2one('approval.matrix.accounting', string="Approval Matrix", compute='_get_approval_matrix')
    approved_matrix_ids = fields.One2many('approval.matrix.accounting.lines', 'monthly_budget_purchase_id', string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.accounting.lines', string='Approval Matrix Line', compute='_get_approve_button')
    request_partner_id = fields.Many2one('res.partner', string="Requested Partner")
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button')
    monthly_purchase_budget_line_carry_in_ids = fields.One2many('monthly.purchase.budget.line', 'monthly_purchase_budget_id', 'Monthly Purchase Budget Carry In Line', domain=[('carry_in_amount', '>', 0)])
    monthly_purchase_budget_line_carry_out_ids = fields.One2many('monthly.purchase.budget.line', 'monthly_purchase_budget_id', 'Monthly Purchase Budget Carry Out Line', domain=[('carry_out_amount', '<', 0)])
    


    def _get_approve_status_from_config(self):
        for record in self:
            record.is_allowed_to_approval_matrix = False
            is_purchase_budget_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_purchase_budget_approval_matrix', False)  
            if is_purchase_budget_approval_matrix:
                record.is_allowed_to_approval_matrix = True

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
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

    @api.depends('company_id', 'branch_id')
    def _get_approval_matrix(self):
        self._get_approve_status_from_config()
        for record in self:
            matrix_id = False
            matrix_id = self.env['approval.matrix.accounting'].search([
                ('company_id', '=', record.company_id.id),
                ('branch_id', '=', record.branch_id.id),
                ('approval_matrix_type', '=', 'purchase_budget')
            ], limit=1)
            record.approval_matrix = matrix_id
            record._compute_approving_matrix_lines()

    @api.onchange('approval_matrix')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.state == 'draft' and record.is_allowed_to_approval_matrix:
                record.approved_matrix_ids = []
                counter = 1
                record.approved_matrix_ids = []
                for rec in record.approval_matrix:
                    for line in rec.approval_matrix_line_ids:
                        data.append((0, 0, {
                            'sequence': counter,
                            'user_ids': [(6, 0, line.user_ids.ids)],
                            'minimum_approver': line.minimum_approver,
                        }))
                        counter += 1
                record.approved_matrix_ids = data

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
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

    def action_request_for_approval(self):
        for record in self:
            record._check_amount()
            record.write({'state': 'to_approve'})
            action_id = self.env.ref('equip3_accounting_budget.action_monthly_purchase_budget')
            template_id = self.env.ref('equip3_accounting_budget.email_template_purchase_budget_matrix_approve_request')
            # wa_template_id = self.env.ref('equip3_accounting_budget.wa_template_request_for_approval_purchase_budget')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=monthly.purchase.budget'
            planned_amount = sum(record.monthly_purchase_budget_line_ids.mapped('planned_amount'))
            currency = ''
            if record.company_id.currency_id.position == 'before':
                currency = record.company_id.currency_id.symbol + str(planned_amount)
            else:
                currency = str(planned_amount) + ' ' + record.company_id.currency_id.symbol
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
                        "currency": currency,
                    }
                    template_id.with_context(ctx).send_mail(record.budget_purchase_id.id, True)
                    phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                    # record.budget_purchase_id._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)
            else:
    
                approver = record.approved_matrix_ids[0].user_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : approver.partner_id.email,
                    'approver_name' : approver.name,
                    'date': date.today(),
                    'submitter' : self.env.user.name,
                    'url' : url,
                    "currency": currency,
                }
                mail1 = template_id.with_context(ctx).send_mail(record.budget_purchase_id.id, True)  
                phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                # record.budget_purchase_id._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)  

    def action_approve(self):
        for record in self:
            action_id = self.env.ref('equip3_accounting_budget.action_monthly_purchase_budget')
            template_id = self.env.ref('equip3_accounting_budget.email_template_purchase_budget_matrix_approve_request')
            template_id_submitter = self.env.ref('equip3_accounting_budget.email_template_approval_of_purchase_budget_action_approve')
            # wa_template_id = self.env.ref('equip3_accounting_budget.wa_template_request_for_approval_purchase_budget')
            # wa_template_id_submitter = self.env.ref('equip3_accounting_budget.wa_template_approval_of_purchase_budget')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=monthly.purchase.budget'
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                planned_amount = sum(record.monthly_purchase_budget_line_ids.mapped('planned_amount'))
                currency = ''
                if record.company_id.currency_id.position == 'before':
                    currency = record.company_id.currency_id.symbol + str(planned_amount)
                else:
                    currency = str(planned_amount) + ' ' + record.company_id.currency_id.symbol
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
                                approver = approving_matrix_line_user
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : approving_matrix_line_user.partner_id.email,
                                    'approver_name' : approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter' : self.env.user.name,
                                    'url' : url,
                                    "date_invoice": record.create_date.date(),
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.budget_purchase_id.id, True)
                                phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                                # record.budget_purchase_id._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                approver = next_approval_matrix_line_id[0].user_ids
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                    'approver_name' : next_approval_matrix_line_id[0].user_ids[0].name,
                                    'date': date.today(),
                                    'submitter' : self.env.user.name,
                                    'url' : url,
                                    "date_invoice":record.create_date.date(),
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.budget_purchase_id.id, True)
                                phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                                # record.budget_purchase_id._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)

            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : self.env.user.partner_id.email,
                    'date': date.today(),
                    'create_date': record.create_date.date(),
                    'submitter' : self.env.user.name,
                    'url' : url
                }
                template_id_submitter.sudo().with_context(ctx).send_mail(record.budget_purchase_id.id, True)
                phone_num = str(record.request_partner_id.mobile) or str(record.request_partner_id.phone)
                # record.budget_purchase_id._send_whatsapp_message_approval_submitter(wa_template_id_submitter, record.request_partner_id.name, phone_num,record.create_date.date())
                record.action_budget_validate()

    @api.model
    def _check_period(self):
        today = date.today()
        budgets = self.search([('date_to', '<', today), ('state', '!=', 'done')])
        for budget in budgets:
            budget.action_budget_done()

    def action_budget_confirm(self):
        self.write({'state': 'confirm'})

    def action_budget_validate(self):
        self._check_amount()
        self.write({'state': 'validate'})

    def action_budget_draft(self):
        self.write({'state': 'draft'})

    def action_budget_cancel(self):
        self.write({'state': 'cancel'})

    def action_budget_done(self):
        # self.write({'state': 'done'})
        for record in self:
            remaining_amount = sum(record.monthly_purchase_budget_line_ids.mapped('remaining_amount'))
            if remaining_amount > 0:

                last_budget_period = self.env['monthly.purchase.budget'].search([('budget_purchase_id', '=', record.budget_purchase_id.id)], order='month_period_id desc', limit=1)
                is_last_period = record.id == last_budget_period.id

                if is_last_period:
                    for line in record.monthly_purchase_budget_line_ids:
                        existing_line = self.env['monthly.purchase.budget.line'].search([
                            ('monthly_purchase_budget_id', '=', record.budget_purchase_id.id),
                            ('group_product_id', '=', line.group_product_id.id),
                            ('product_id', '=', line.product_id.id)
                        ], limit=1)

                        existing_line.write({'planned_amount': line.remaining_amount})
                    budget_purchase_id = record.budget_purchase_id
                    budget_purchase_id.write({'state': 'done'})
                    for child in budget_purchase_id.child_budget_ids:
                        child.write({'state': 'done'})

                else:
                    next_period = record.month_period_id.id + 1
                    next_month_period = self.env['month.period'].search([('id','=',next_period)], limit=1)
                    if next_month_period:
                        next_monthly_budget = self.env['monthly.purchase.budget'].search([('budget_purchase_id','=',record.budget_purchase_id.id),('month_period_id','=',next_month_period.id)], limit=1)
                        if next_monthly_budget:
                            for line in record.monthly_purchase_budget_line_ids:
                                existing_line = self.env['monthly.purchase.budget.line'].search([
                                    ('monthly_purchase_budget_id', '=', next_monthly_budget.id),
                                    ('group_product_id', '=', line.group_product_id.id),
                                    ('product_id', '=', line.product_id.id)
                                ], limit=1)

                                if existing_line:
                                    # Update the planned amount of the existing line
                                    existing_line.write({
                                        'planned_amount': existing_line.planned_amount + line.remaining_amount,
                                        'carry_in_amount': line.remaining_amount,
                                        'month_period_origin_id': record.month_period_id.id
                                    })
                                else:
                                    # Create a new line if it doesn't exist
                                    self.env['monthly.purchase.budget.line'].create({
                                        'monthly_purchase_budget_id': next_monthly_budget.id,
                                        'group_product_id': line.group_product_id.id,
                                        'product_id': line.product_id.id,
                                        'planned_amount': line.remaining_amount,
                                        'carry_in_amount': line.remaining_amount,
                                        'month_period_origin_id': record.month_period_id.id,
                                        'account_tag_ids': [(6, 0, line.account_tag_ids.ids)]
                                    })
                                
                                line.write({'carry_out_amount': -line.remaining_amount,
                                           'month_period_source_id': next_month_period.id})
            record.write({'state': 'done'})
                    
    def action_confirm_budget_done(self):

        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Confirm Budget Done',
        #     'res_model': 'monthly.purchase.budget.confirm',
        #     'view_mode': 'form',
        #     'target': 'new',
        #     'context': {
        #         'active_id': self.id,
        #     },
        # }

        # message = ''
        last_budget_period = self.env['monthly.purchase.budget'].search([('budget_purchase_id', '=', self.budget_purchase_id.id)], order='month_period_id desc', limit=1)
        is_last_period = self.id == last_budget_period.id

        if is_last_period:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Confirm Budget Done',
                'res_model': 'monthly.purchase.budget.end.period',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'active_id': self.id,
                },
            }
            # raise ValidationError(message)
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Confirm Budget Done',
                'res_model': 'monthly.purchase.budget.next.period',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'active_id': self.id,
                },
            }
        
        # Set the appropriate message
        # if is_last_period:
        #     message = "Are you sure you want to mark this budget as done? The remaining amount will be returned to %s." % self.budget_purchase_id.name
        # else:
        #     message = "Are you sure you want to mark this budget as done? The remaining amount will be carried over to the next period."

        # raise ValidationError(message)

    def action_reject(self):
        self.write({'state': 'rejected'})

    @api.depends('month_period_id')
    def _compute_date(self):
        for rec in self:
            month_period = rec.month_period_id.name
            date_from = datetime.strptime(month_period, '%B %Y').replace(day=1).date()
            # Get the last day of the month
            last_day = calendar.monthrange(date_from.year, date_from.month)[1]
            # Return the last day of the month in the format "YYYY-MM-DD"
            date_to = datetime(date_from.year, date_from.month, last_day).date()

            if date_from < rec.budget_purchase_id.date_from:
                date_from = rec.budget_purchase_id.date_from
            if date_to > rec.budget_purchase_id.date_to:
                date_to = rec.budget_purchase_id.date_to

            rec.date_from = date_from
            rec.date_to = date_to

    @api.depends('monthly_purchase_budget_line_ids.planned_amount','monthly_purchase_budget_line_ids.practical_amount','monthly_purchase_budget_line_ids.remaining_amount')
    def _compute_amount(self):
        for rec in self:
            planned_amount = practical_amount = remaining_amount = avail_amount = reserve_amount = 0
            for line in rec.monthly_purchase_budget_line_ids:
                planned_amount += line.planned_amount
                practical_amount += line.practical_amount
                remaining_amount += line.remaining_amount
                avail_amount += line.avail_amount
                reserve_amount += line.reserve_amount

            rec.total_line_planned_amount = planned_amount
            rec.total_line_practical_amount = practical_amount
            rec.total_line_remaining_amount = remaining_amount
            rec.total_line_avail_amount = avail_amount
            rec.total_line_reserve_amount = reserve_amount


    @api.depends('budget_purchase_id.account_tag_ids')
    def _compute_account_tag_ids_domain(self):
        if self.budget_purchase_id:
            self.account_tag_ids_domain = json.dumps([('id','in',self.budget_purchase_id.account_tag_ids.ids)])
        else:
            self.account_tag_ids_domain = json.dumps([])

    @api.depends('budget_purchase_id')
    def _compute_month_period_id_domain(self):
        month_ids = []
        if self.budget_purchase_id:
            month_list = pd.date_range(start=pd.to_datetime(self.budget_purchase_id.date_from).to_period('M').start_time, end=pd.to_datetime(self.budget_purchase_id.date_to).to_period('M').start_time, freq='MS').strftime("%B %Y").tolist()
            for month in month_list:
                month_period_id = self.env['month.period'].search([('name','=',month)], limit=1)
                if not month_period_id:
                    month_period_id = self.env['month.period'].create({'name': month})
                month_ids.append(month_period_id.id)

        self.month_period_id_domain = json.dumps([('id','in',month_ids)])

    @api.onchange('budget_purchase_id')
    def _onchange_budget_purchase_id(self):
        for rec in self:
            if rec.budget_purchase_id:
                if rec.budget_purchase_id.date_from <= date.today():
                    rec.state = 'validate'
                if rec.budget_purchase_id.date_to > date.today():
                    rec.state = 'done'

    def _check_amount(self):
        for rec in self:
            rec.budget_purchase_id._compute_total_line()
            if rec.total_line_planned_amount > rec.total_avail_amount:
                raise ValidationError(_('Total Planned Amount Monthly Purchase Budget is greater than Available Budget!'))

    def unlink(self):
        for record in self:
            if record.state in ['validate', 'done']:
                raise ValidationError(_('You cannot delete a budget in state \'%s\'.') % (record.state))
        return super(MonthlyPurchaseBudget, self).unlink()


class MonthlyPurchaseBudgetLine(models.Model):
    _name = "monthly.purchase.budget.line"
    _description = "Monthly Purchase Budget Line"

    
    monthly_purchase_budget_id = fields.Many2one('monthly.purchase.budget', 'Monthly Budget', ondelete='cascade', index=True, required=True)
    purchase_budget_id = fields.Many2one('budget.purchase', string='Budget Purchase', related='monthly_purchase_budget_id.budget_purchase_id', store=True)
    month_period_id = fields.Many2one('month.period', 'Month', related='monthly_purchase_budget_id.month_period_id')
    group_product_id = fields.Many2one('account.product.group', string="Group of Product")
    group_product_id_domain = fields.Char(string='Group Product Domain', compute='_compute_product_domain')
    product_id = fields.Many2one('product.product', string="Product")
    product_id_domain = fields.Char(string='Product Domain', compute='_compute_product_domain')
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    account_tag_ids_domain = fields.Char(string='Analytic Group Domain', compute='_compute_account_tag_ids_domain')
    currency_id = fields.Many2one('res.currency', related='monthly_purchase_budget_id.budget_purchase_id.currency_id', readonly=True)
    planned_amount = fields.Monetary('Planned Amount', required=True, currency_field="currency_id")
    avail_amount = fields.Monetary(string="Available to Reserve", compute="_compute_amount", currency_field="currency_id")
    reserve_amount = fields.Monetary(string="Reserved Amount", compute="_compute_amount", currency_field="currency_id")
    practical_amount = fields.Monetary(string='Used Amount', compute="_compute_amount", currency_field="currency_id")
    remaining_amount = fields.Monetary(string='Remaining Amount', compute="_compute_amount", currency_field="currency_id")
    auto_carry_next_period = fields.Monetary(string="Auto Carry Next Period")
    carry_in_amount = fields.Monetary(string="Carry In Amount")
    carry_out_amount = fields.Monetary(string="Carry Out Amount")
    month_period_origin_id = fields.Many2one('month.period', 'Origin Month Period', )
    month_period_source_id = fields.Many2one('month.period', 'Source Month Period', )

    # def _compute_month_period_origin_id(self):
    #     for rec in self:
    #         rec.month_period_origin_id = rec.monthly_purchase_budget_id.month_period_id

    # def _compute_month_period_source_id(self):
    #     for rec in self:
    #         rec.month_period_source_id = rec.monthly_purchase_budget_id.month_period_id + 1

    @api.depends('monthly_purchase_budget_id')
    def _compute_budget_purchase_id(self):
        for record in self:
            record.budget_purchase_id = record.monthly_purchase_budget_id.budget_purchase_id if record.monthly_purchase_budget_id else False

    @api.depends('monthly_purchase_budget_id.budget_purchase_id')
    def _compute_product_domain(self):
        if self.monthly_purchase_budget_id.budget_purchase_id:
            group_product_ids = []
            product_ids = []

            for line in self.monthly_purchase_budget_id.budget_purchase_id.purchase_budget_line:
                group_product_ids.append(line.group_product_id.id)
                product_ids.append(line.product_id.id)

            self.group_product_id_domain = json.dumps([('id','in',group_product_ids)])
            self.product_id_domain = json.dumps([('id','in',product_ids),('product_tmpl_id.group_product', '=', False)])
        else:
            self.group_product_id_domain = json.dumps([])
            self.product_id_domain = json.dumps([('product_tmpl_id.group_product', '=', False)])

    @api.depends('monthly_purchase_budget_id.budget_purchase_id')
    def _compute_account_tag_ids_domain(self):
        if self.monthly_purchase_budget_id.budget_purchase_id:
            self.account_tag_ids_domain = json.dumps([('id','in',self.monthly_purchase_budget_id.budget_purchase_id.account_tag_ids.ids)])

    def action_open_purchase_order_lines(self):
        action = self.env['ir.actions.act_window']._for_xml_id('equip3_purchase_operation.product_purchase_orders_line')
        
        purchase_ids = []
        date_from = self.monthly_purchase_budget_id.date_from
        date_to = self.monthly_purchase_budget_id.date_to

        domain = [('state','=','purchase'),('is_use_purchase_budget','=',True)]
        if self.group_product_id:
            domain += [('product_template_id.group_product', '=', self.group_product_id.id)]
        elif self.product_id:
            domain += [('product_template_id','=',self.product_id.product_tmpl_id.id)]

        purchase_lines = self.env['purchase.order.line'].search(domain)
        for purchase_id in purchase_lines:
            is_correct = False
            if purchase_id.order_id.from_purchase_request:
                purchase_request = self.env['purchase.request'].search([('name','=',purchase_id.order_id.origin)], limit=1)
                if purchase_request.request_date <= date_to and purchase_request.request_date >= date_from:
                    is_correct = True
            else:
                if purchase_id.date_planned.date() <= date_to and purchase_id.date_planned.date() >= date_from:
                    is_correct = True

            if is_correct:
                if any(item in self.account_tag_ids.ids for item in purchase_id.analytic_tag_ids.ids):
                    purchase_ids.append(purchase_id.id)
        action['domain'] = [('id','in',purchase_ids)]

        # action['domain'] = [('date_planned','>=',self.monthly_purchase_budget_id.date_from),('date_planned','<=',self.monthly_purchase_budget_id.date_to),('state','=','purchase'),('is_use_purchase_budget','=',True)]

        # if self.group_product_id:
        #     action['domain'] += [('product_template_id.group_product', '=', self.group_product_id.id)]
        # elif self.product_id:
        #     action['domain'] += [('product_template_id', '=', self.product_id.product_tmpl_id.id)]
        
        # if self.account_tag_ids.ids:
        #     action['domain'] += [('analytic_tag_ids','in',self.account_tag_ids.ids)]

        return action

    def action_open_purchase_request_lines(self):
        action = self.env['ir.actions.act_window']._for_xml_id('purchase_request.purchase_request_line_form_action')
        action['domain'] = [('request_id.request_date','>=',self.monthly_purchase_budget_id.date_from),('request_id.request_date','<=',self.monthly_purchase_budget_id.date_to),('request_id.pr_state','=','purchase_request'),('is_use_purchase_budget','=',True)]

        if self.group_product_id:
            action['domain'] += [('product_id.product_tmpl_id.group_product', '=', self.group_product_id.id)]
        elif self.product_id:
            action['domain'] += [('product_id', '=', self.product_id.id)]
        
        if self.account_tag_ids.ids:
            action['domain'] += [('analytic_account_group_ids','in',self.account_tag_ids.ids)]

        return action

    @api.depends('group_product_id','account_tag_ids','product_id','planned_amount','practical_amount','reserve_amount','avail_amount','remaining_amount')
    def _compute_amount(self):
        for record in self:
            date_from = record.monthly_purchase_budget_id.date_from
            date_to = record.monthly_purchase_budget_id.date_to

            record.avail_amount = 0
            record.reserve_amount = 0
            record.practical_amount = 0
            record.remaining_amount = 0

            if record.group_product_id and record.account_tag_ids:
                purchase_ids= self.env['purchase.order.line'].search(
                    [
                        ('product_template_id.group_product','=',record.group_product_id.id),
                        # ('analytic_tag_ids','in',record.account_tag_ids.ids),
                        # ('date_planned','<=',date_to),
                        # ('date_planned','>=',date_from),
                        ('state','=','purchase'),
                        ('is_use_purchase_budget','=',True),
                    ]
                )
                total = 0                    
                for purchase_id in purchase_ids:
                    is_correct = False
                    if purchase_id.order_id.from_purchase_request:
                        purchase_request = self.env['purchase.request'].search([('name','=',purchase_id.order_id.origin)], limit=1)
                        if purchase_request.request_date <= date_to and purchase_request.request_date >= date_from:
                            is_correct = True
                    else:
                        if purchase_id.date_planned.date() <= date_to and purchase_id.date_planned.date() >= date_from:
                            is_correct = True

                    if is_correct:
                        if any(item in record.account_tag_ids.ids for item in purchase_id.analytic_tag_ids.ids):
                            total += purchase_id.currency_id._convert((purchase_id.price_unit * purchase_id.product_qty), record.currency_id, record.monthly_purchase_budget_id.company_id, purchase_id.date_planned)
                record.practical_amount=total
                reserve_amount = 0
                reserve_ids = self.env['purchase.request.line'].search(
                    [
                        ('request_id.request_date', '>=', date_from), ('request_id.request_date', '<=', date_to), 
                        ('request_state','in',['purchase_request','approved']),
                        ('request_id.purchase_req_state','not in',['done','cancel']),
                        ('product_id.group_product','=',record.group_product_id.id),
                        # ('analytic_account_group_ids','in',record.account_tag_ids.ids),
                        ('is_use_purchase_budget','=',True),
                    ]
                )

                for reserve_id in reserve_ids:
                    if any(item in record.account_tag_ids.ids for item in reserve_id.analytic_account_group_ids.ids):
                        actual_amount = reserve_id.price_total - reserve_id.po_actual_amount
                        if actual_amount < 0:
                            actual_amount = 0
                        reserve_amount += reserve_id.currency_id._convert(actual_amount, record.currency_id, record.monthly_purchase_budget_id.company_id, reserve_id.date_start)
                record.reserve_amount = reserve_amount
            elif record.product_id and record.account_tag_ids:
                purchase_ids= self.env['purchase.order.line'].search(
                    [
                        ('product_template_id','=',record.product_id.product_tmpl_id.id),
                        # ('analytic_tag_ids','in',record.account_tag_ids.ids),
                        # ('date_planned','<=',date_to),
                        # ('date_planned','>=',date_from),
                        ('state','=','purchase'),
                        ('is_use_purchase_budget','=',True),
                    ]
                )
                total = 0                    
                for purchase_id in purchase_ids:
                    is_correct = False
                    if purchase_id.order_id.from_purchase_request:
                        purchase_request = self.env['purchase.request'].search([('name','=',purchase_id.order_id.origin)], limit=1)
                        if purchase_request.request_date <= date_to and purchase_request.request_date >= date_from:
                            is_correct = True
                    else:
                        if purchase_id.date_planned.date() <= date_to and purchase_id.date_planned.date() >= date_from:
                            is_correct = True

                    if is_correct:
                        if any(item in record.account_tag_ids.ids for item in purchase_id.analytic_tag_ids.ids):
                            total += purchase_id.currency_id._convert((purchase_id.price_unit * purchase_id.product_qty), record.currency_id, record.monthly_purchase_budget_id.company_id, purchase_id.date_planned)
                record.practical_amount=total

                reserve_amount = 0
                reserve_ids = self.env['purchase.request.line'].search(
                    [
                        ('request_id.request_date', '>=', date_from), ('request_id.request_date', '<=', date_to), 
                        ('request_state','in',['purchase_request','approved']),
                        ('request_id.purchase_req_state','not in',['done','cancel']),
                        ('product_id','=',record.product_id.id),
                        # ('analytic_account_group_ids','in',record.account_tag_ids.ids),
                        ('is_use_purchase_budget','=',True),
                    ]
                )
                for reserve_id in reserve_ids:
                    if any(item in record.account_tag_ids.ids for item in reserve_id.analytic_account_group_ids.ids):
                        actual_amount = reserve_id.price_total - reserve_id.po_actual_amount
                        if actual_amount < 0:
                            actual_amount = 0
                        reserve_amount += reserve_id.currency_id._convert(actual_amount, record.currency_id, record.monthly_purchase_budget_id.company_id, reserve_id.date_start)
                record.reserve_amount = reserve_amount
            else:
                record.practical_amount=0

            # auto_carry_next_period = record.auto_carry_next_period
            # if auto_carry_next_period < 0:
            #     auto_carry_next_period = record.auto_carry_next_period * -1
            # record.avail_amount = record.planned_amount - record.practical_amount - record.reserve_amount
            # record.remaining_amount = record.planned_amount - record.practical_amount
            record.avail_amount = record.planned_amount - record.practical_amount - record.reserve_amount
            record.remaining_amount = record.planned_amount + record.carry_out_amount - record.practical_amount
            record.monthly_purchase_budget_id._compute_amount()

    @api.constrains('planned_amount')
    def _check_amount(self):
        for line in self:
            if line.planned_amount < 0:
                raise ValidationError(_('Planned Amount cannot be minus!'))


class MonthPeriod(models.Model):
    _name = "month.period"
    _description = "Month Period"

    name = fields.Char('Name')