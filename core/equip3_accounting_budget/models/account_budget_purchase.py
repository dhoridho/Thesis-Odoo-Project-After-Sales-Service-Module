# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
import pytz
from odoo import tools
import requests
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
import json
import pandas as pd

headers = {'content-type': 'application/json'}

class purchaseBudget(models.Model):
    _name = "budget.purchase"
    _description = "Purchase Budget"
    _inherit = ['mail.thread']
    _rec_name = 'complete_name'


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        domain=_domain_branch,
        default = _default_branch,
        readonly=False)

    name = fields.Char('Purchase Budget Name', required=True, states={'done': [('readonly', True)]})
    
    parent_id = fields.Many2one(
        'crossovered.budget',
        'Budget Account Reference',
        index=True,
        ondelete='cascade',
        domain=[
            ('state', '=', 'validate'),
        ]
    )
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    date_from = fields.Date('Start Date', required=True, states={'done': [('readonly', True)]})
    date_to = fields.Date('End Date', required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),         
        ('confirm', 'Confirmed'),
        ('to_approve', 'Waiting For Approval'),
        ('rejected', 'Rejected'),
        ('validate', 'Validated'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], 'Status', default='draft',compute="_compute_autodone_schedule1", store=True, index=True, required=True, readonly=True, copy=False, tracking=True)
    state1 = fields.Selection(related="state", tracking=False)
    state2 = fields.Selection(related="state", tracking=False)
    purchase_budget_line = fields.One2many('budget.purchase.lines', 'purchase_budget_id', 'Budget Lines',
                                            states={'done': [('readonly', True)]}, copy=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    # branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.user.branch_id.id)
    
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")

    approval_matrix = fields.Many2one('approval.matrix.accounting', string="Approval Matrix",
                                      compute='_get_approval_matrix')
    request_partner_id = fields.Many2one('res.partner', string="Requested Partner")
    is_allowed_to_approval_matrix = fields.Boolean(string="Is Allowed Approval Matrix",
                                                   compute='_get_approve_status_from_config')
    is_allowed_to_wa_notification = fields.Boolean(string="Is Allowed WA Notification", compute='_get_approve_status_from_config')
    approved_matrix_ids = fields.One2many('approval.matrix.accounting.lines', 'budget_purchase_id',
                                          string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.accounting.lines', string='Approval Matrix Line',
                                              compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    purchase_lines_id = fields.Many2one('purchase.order.line', string='Purchase Lines', store=True)
    purchase_line_subtotal = fields.Monetary(related='purchase_lines_id.price_subtotal', string='Purchase Lines Subtotal',
                                            store=True,readonly=True)
    date_today = fields.Date(string='Today Date', compute="_compute_autodone_schedule1", store=True, default=fields.Date.today())
    is_use_theoretical_achievement = fields.Boolean(string="Is use Theoritical amount and Achievement", compute="_get_use_theoretical_achievement_config")
    total_planned_amount = fields.Float(compute='_compute_total_line',string="Planned Amount")
    total_practical_amount = fields.Float(compute='_compute_total_line',string="Purchased Amount")
    total_remaining_amount = fields.Float(compute='_compute_total_line',string="Remaining Amount", store=True)
    total_avail_amount = fields.Float(compute='_compute_total_line',string="Available Amount")
    total_reserve_amount = fields.Float(compute='_compute_total_line',string="Reserve Amount")
    is_parent_budget = fields.Boolean(string="Is Parent Budget", default=False)
    parent_budget_id = fields.Many2one('budget.purchase', 'Parent Budget', index=True, ondelete='cascade')
    child_budget_ids = fields.One2many('budget.purchase', 'parent_budget_id', string='Child Budgets')
    account_tag_ids_domain = fields.Char(string='Analytic Group Domain', compute='_compute_account_tag_ids_domain')
    total_monthly_budget = fields.Integer(string="Monthly Budget", compute='_compute_total_monthly_budget')
    budget_purchase_carry_in_line_ids = fields.One2many('budget.purchase.carry.over.lines', 'new_budget_purchase_id', string='Budget Carry In Lines')
    budget_purchase_carry_out_line_ids = fields.One2many('budget.purchase.carry.over.lines', 'budget_purchase_id', string='Budget Carry Out Lines')
    # monthly_purchase_budget_carry_in_ids = fields.One2many('monthly.purchase.budget', 'budget_purchase_id', string='Budget Carry In Lines')
    # monthly_purchase_budget_line_carry_in_ids = fields.One2many('monthly.purchase.budget.line', 'purchase_budget_id', string='Budget Carry In Lines', domain=[('carry_in_amount', '>', 0)])
    # monthly_purchase_budget_line_carry_out_ids = fields.One2many('monthly.purchase.budget.line', 'purchase_budget_id', string='Budget Carry Out Lines', domain=[('carry_out_amount', '<', 0)])

    @api.depends('name', 'parent_budget_id.complete_name')
    def _compute_complete_name(self):
        for record in self:
            if record.parent_budget_id:
                record.complete_name = '%s / %s' % (record.parent_budget_id.complete_name, record.name)
            else:
                record.complete_name = record.name

    def _compute_total_monthly_budget(self):
        for rec in self:
            self.env.cr.execute(
                "SELECT count(*) FROM monthly_purchase_budget WHERE budget_purchase_id = %s",
                (rec.id,))
            total_monthly_budget = self.env.cr.fetchone()[0]
            rec.total_monthly_budget = total_monthly_budget

    @api.depends('parent_budget_id.account_tag_ids', 'parent_id.account_tag_ids')
    def _compute_account_tag_ids_domain(self):
        for rec in self:
            account_tag_ids_to_domain = []
            if rec.parent_id and rec.parent_id.account_tag_ids:
                account_tag_ids_to_domain.extend(rec.parent_id.account_tag_ids.ids)
            if rec.parent_budget_id and rec.parent_budget_id.account_tag_ids:
                account_tag_ids_to_domain.extend(rec.parent_budget_id.account_tag_ids.ids)

            if account_tag_ids_to_domain:
                rec.account_tag_ids_domain = json.dumps([('id','in', account_tag_ids_to_domain)])
            else:
                rec.account_tag_ids_domain = json.dumps([])

    @api.depends('purchase_budget_line.planned_amount','purchase_budget_line.practical_amount','purchase_budget_line.remaining_amount','purchase_budget_line.avail_amount','purchase_budget_line.reserve_amount')
    def _compute_total_line(self):
        for data in self:
            total_planned_amount = 0
            total_practical_amount = 0
            total_remaining_amount = 0
            total_avail_amount = 0
            total_reserve_amount = 0

            for line in data.purchase_budget_line:
                line._compute_fields_practical()

            if data.purchase_budget_line:
                total_avail_amount += sum([line.avail_amount for line in data.purchase_budget_line])
                total_planned_amount += sum([line.planned_amount for line in data.purchase_budget_line])
                total_practical_amount += sum([line.practical_amount for line in data.purchase_budget_line])
                total_remaining_amount += sum([line.remaining_amount for line in data.purchase_budget_line])
                total_reserve_amount += sum([line.reserve_amount for line in data.purchase_budget_line])
            data.total_planned_amount = total_planned_amount
            data.total_practical_amount = total_practical_amount
            data.total_remaining_amount = total_remaining_amount
            data.total_avail_amount = total_avail_amount
            data.total_reserve_amount = total_reserve_amount
                
    def unlink(self):
        for record in self:
            if record.state1 in ['validate', 'done']:
                raise ValidationError(_('You cannot delete a budget in state \'%s\'.') % (record.state,))
        return super(purchaseBudget, self).unlink()
    

    # @api.constrains('parent_id')
    # def _check_category_recursion(self):
    #     if not self._check_recursion():
    #         raise ValidationError(_('You cannot create recursive categories.'))
    #     return True

    # @api.onchange('')
    # def _onchange_(self):
    #     pass


    def action_budget_confirm(self):
        for line in self.purchase_budget_line:
            line._check_amount()
        # self.write({'state': 'confirm'})
        self.action_budget_validate()

    def action_budget_draft(self):
        self.write({'state': 'draft'})

    def action_budget_validate(self):
        self.write({'state': 'validate'})
    
    def action_budget_undone(self):
        self.write({'state': 'validate'})

    def action_budget_cancel(self):
        self.write({'state': 'cancel'})
            
        for child in self.child_budget_ids:
            child.action_budget_cancel()

        monthly_purchase_budget = self.env['monthly.purchase.budget'].search([('budget_purchase_id','=',self.id)])
        for data in monthly_purchase_budget:
            data.action_budget_cancel()

    def action_budget_done(self):
        if self.total_reserve_amount > 0:
            raise ValidationError(_("You cannot set this budget to done because this budget is reserved."))

        self.write({'state': 'done'})
        for child in self.child_budget_ids:
            child.write({'state': 'done'})

        monthly_purchase_budget = self.env['monthly.purchase.budget'].search([('budget_purchase_id','=',self.id)])
        for data in monthly_purchase_budget:
            data.action_budget_done()

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
            
    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        self._get_approve_status_from_config()
        if self.parent_id:
            self.is_parent_budget = False

    @api.depends('date_today','purchase_budget_line.practical_amount_temp')
    def _compute_autodone_schedule1(self):
        for record in self.search([('state','!=','done')]):
            today = fields.Date.today()
            if today > record.date_to:
                record.update({'state':'done'})

    def _get_approve_status_from_config(self):
        for record in self:
            # record.is_allowed_to_approval_matrix = False
            # is_purchase_budget_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_purchase_budget_approval_matrix', False)
            # if is_purchase_budget_approval_matrix:
            #     record.is_allowed_to_approval_matrix = True
            record.is_allowed_to_approval_matrix = self.env['accounting.config.settings'].search([], limit=1).is_allow_purchase_budget_approval_matrix
            record.is_allowed_to_wa_notification = self.env['accounting.config.settings'].search([], limit=1).is_allow_purchase_budget_wa_notification


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

    def _send_wa_request_for_approval_purchase_budget(self, approver, phone_num, currency, url, submitter):
            wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_request_approval_purchase_budget_1')
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
            for line in record.purchase_budget_line:
                line._check_amount()
            record.write({'state': 'to_approve'})
            action_id = self.env.ref('equip3_accounting_budget.action_account_purchase_budget_view')
            template_id = self.env.ref('equip3_accounting_budget.email_template_purchase_budget_matrix_approve_request')
            # wa_template_id = self.env.ref('equip3_accounting_budget.wa_template_request_for_approval_purchase_budget')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=budget.purchase'
            planned_amount = sum(record.purchase_budget_line.mapped('planned_amount'))
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
                    template_id.with_context(ctx).send_mail(record.id, True)
                    phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                    if record.is_allowed_to_wa_notification:
                        record._send_wa_request_for_approval_purchase_budget(approver, phone_num, currency, url, self.env.user.name)
                    # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)
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
                mail1 = template_id.with_context(ctx).send_mail(record.id, True)  
                phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                if record.is_allowed_to_wa_notification:
                    record._send_wa_request_for_approval_purchase_budget(approver, phone_num, currency, url, self.env.user.name)
                # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)  

    def _send_wa_reject_purchase_budget(self, submitter, phone_num, created_date, approver = False, reason = False):
        wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_rejection_purchase_budget_1')
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

    def _send_wa_approval_purchase_budget(self, approver, phone_num, created_date, submitter):
        wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_approval_purchase_budget_1')
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
            action_id = self.env.ref('equip3_accounting_budget.action_account_purchase_budget_view')
            template_id = self.env.ref('equip3_accounting_budget.email_template_purchase_budget_matrix_approve_request')
            template_id_submitter = self.env.ref('equip3_accounting_budget.email_template_approval_of_purchase_budget_action_approve')
            # wa_template_id = self.env.ref('equip3_accounting_budget.wa_template_request_for_approval_purchase_budget')
            # wa_template_id_submitter = self.env.ref('equip3_accounting_budget.wa_template_approval_of_purchase_budget')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=budget.purchase'
            created_date = record.create_date.date()
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                planned_amount = sum(record.purchase_budget_line.mapped('planned_amount'))
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
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                                if record.is_allowed_to_wa_notification:
                                    record._send_wa_approval_purchase_budget(approver, phone_num, record.create_date.date(), self.env.user.name)
                                # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)
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
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                                if record.is_allowed_to_wa_notification:
                                    record._send_wa_approval_purchase_budget(approver, phone_num, record.create_date.date(), self.env.user.name)
                                # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)

            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : self.env.user.partner_id.email,
                    'date': date.today(),
                    'create_date': record.create_date.date(),
                    'submitter' : self.env.user.name,
                    'url' : url
                }
                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                phone_num = str(record.request_partner_id.mobile) or str(record.request_partner_id.phone)
                if record.is_allowed_to_wa_notification:
                    record._send_wa_approval_purchase_budget(record.request_partner_id, phone_num, record.create_date.date(), self.env.user.name)
                # record._send_whatsapp_message_approval_submitter(wa_template_id_submitter, record.request_partner_id.name, phone_num,record.create_date.date())

                record.action_budget_confirm()
                record.action_budget_validate()
                
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

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Budget ',
            'res_model': 'budget.purchase.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.depends('name')
    def _get_use_theoretical_achievement_config(self):
        is_use_theoretical_achievement = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_budget.accounting_budget_use_theoretical_achievement', False)
        self.is_use_theoretical_achievement = is_use_theoretical_achievement

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        for rec in self:
            if rec.parent_id:
                if rec.date_from < rec.parent_id.date_from or rec.date_to > rec.parent_id.date_to:
                    raise ValidationError(_('The date is out of the Budget Account Reference period!'))
            if rec.parent_budget_id:
                if rec.date_from < rec.parent_budget_id.date_from or rec.date_to > rec.parent_budget_id.date_to:
                    raise ValidationError(_('Period is out of the Parent Budget period!'))

    @api.onchange('parent_budget_id')
    def _onchange_parent_budget_id(self):
        for record in self:
            if record.parent_budget_id:
                record.date_from = record.parent_budget_id.date_from
                record.date_to = record.parent_budget_id.date_to

    def action_generate_monthly_budget(self):
        month_list = pd.date_range(start=pd.to_datetime(self.date_from).to_period('M').start_time, end=pd.to_datetime(self.date_to).to_period('M').start_time, freq='MS').strftime("%B %Y").tolist()        
        for month in month_list:
            month_period_id = self.env['month.period'].search([('name','=',month)], limit=1)
            if not month_period_id:
                month_period_id = self.env['month.period'].create({'name': month})

            name = ''.join(word[0].upper() for word in self.name.split())[:4]
            month = datetime.strptime(month, "%B %Y").strftime("%b/%Y")

            vals = {
                'name': '%s/%s' % (name, month),
                'budget_purchase_id': self.id,
                'month_period_id': month_period_id.id,
                'account_tag_ids': self.account_tag_ids.ids
            }
            self.env['monthly.purchase.budget'].create(vals)

    def action_view_monthly_budget(self):
        return {
            'name': ("Monthly Purchase Budget"),
            'view_mode': 'tree,form',
            'res_model': 'monthly.purchase.budget',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('budget_purchase_id', '=', self.id)],
            'context': {'group_by': 'budget_purchase_id'}
        }

    @api.onchange('account_tag_ids')
    def _onchange_account_tag_ids(self):
        for line in self.purchase_budget_line:
            line.account_tag_ids = line.purchase_budget_id.account_tag_ids.ids

    @api.onchange('date_from','date_to') 
    def _onchange_budget_date_period(self):
        for line in self.purchase_budget_line:
            line.date_from = line.purchase_budget_id.date_from
            line.date_to = line.purchase_budget_id.date_to

    def write(self, vals):
        result = super(purchaseBudget, self).write(vals)
        for req in self:
            if vals.get('state') in ['to_approve','confirm','validate']:
                if req.parent_id and req.parent_budget_id and req.parent_budget_id.parent_id:
                   raise ValidationError('You cannot set Budget Account Reference because parent budget has already referenced to Budget Account!') 

                if req.parent_id:
                    for line in req.purchase_budget_line:
                        budget_domain = [
                            ('general_budget_id', '=', line.product_budget.id),
                            ('crossovered_budget_id', '=', req.parent_id.id)
                        ]
                        if line.account_tag_ids:
                            budget_domain += [('account_tag_ids', 'in', line.account_tag_ids.ids)]
                        crossovered_budget_lines = self.env['crossovered.budget.lines'].search(budget_domain)

                        same_budget_lines = self.env['budget.purchase.lines'].search([
                            ('product_budget', '=', line.product_budget.id),
                            ('parent_id', '=', req.parent_id.id),
                            ('purchase_budget_id', '=', req.id),
                            ('account_tag_ids', 'in', line.account_tag_ids.ids)
                        ])
                        if crossovered_budget_lines and sum(same_budget_lines.mapped('planned_amount')) > crossovered_budget_lines.available_child_purchase_amount:
                            raise ValidationError('You cannot allocate more than the budget account reference amount.')

        return result

    @api.onchange('is_parent_budget') 
    def _onchange_is_parent_budget(self):
        for budget in self:
            if budget.is_parent_budget:
                budget.account_tag_ids = False
                for line in budget.purchase_budget_line:
                    line.account_tag_ids = False

class ApprovalMatrixAccountingLines(models.Model):
    _inherit = "approval.matrix.accounting.lines"

    budget_purchase_id = fields.Many2one('budget.purchase', string='Account Budget')
    monthly_budget_purchase_id = fields.Many2one('monthly.purchase.budget', string='Monthly Budget Purchase')


class PurchaseBudgetLines(models.Model):
    _name = "budget.purchase.lines"
    _description = "Budget Line"

    name = fields.Char(compute='_compute_line_name')
    purchase_budget_id = fields.Many2one('budget.purchase', 'Budget',ondelete='cascade', index=True,
                                            required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    analytic_group_id = fields.Many2one('account.analytic.group', 'Analytic Group',
                                        related='analytic_account_id.group_id', readonly=True)
    product_budget = fields.Many2one('account.budget.post', 'Budgetary Position')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    paid_date = fields.Date('Paid Date')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    planned_amount = fields.Monetary(
        'Planned Amount', required=True,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.")
    practical_amount = fields.Monetary(string='Purchased Amount', compute="_compute_fields_practical", help="Amount really earned/spent.")
    practical_amount_temp = fields.Monetary(string='Purchased Amount', store=True)
    remaining_amount = fields.Monetary(string='Remaining Amount', compute="_compute_remaining_amount")
    theoritical_amount = fields.Monetary(
        compute='_compute_theoritical_amount', string='Theoretical Amount',
        help="Amount you are supposed to have earned/spent at this date.")
    percentage = fields.Float(
        compute='_compute_percentage', string='Achievement',
        help="Comparison between practical and theoretical amount. This measure tells you if you are below or over budget.")
    company_id = fields.Many2one(related='purchase_budget_id.company_id', comodel_name='res.company',
                                 string='Company', store=True, readonly=True)
    is_above_budget = fields.Boolean(compute='_is_above_budget')
    purchase_budget_state = fields.Selection(related='purchase_budget_id.state', string='Budget State',
                                            store=True,readonly=True)
    parent_analytic_account_id = fields.Many2one('account.analytic.account', 'Parent Analytic Account')
    
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    product_id = fields.Many2one('product.product', string="Product")
    purchase_order_line_budget_id = fields.Many2one(string="Budget Purchase Line", comodel_name="purchase.order.line", help="Budget Purchase Order Line")
    group_product_id = fields.Many2one('account.product.group', string="Group of Product")
    avail_amount = fields.Monetary(string="Available to Reserve", compute="_compute_fields_practical", store=False)
    reserve_amount = fields.Monetary(string="Reserved Amount", compute="_compute_fields_practical")
    group_product_id_domain = fields.Char(string='Group Product Domain', compute='_compute_product_domain')
    product_id_domain = fields.Char(string='Product Domain', compute='_compute_product_domain')
    account_tag_ids_domain = fields.Char(string='Analytic Group Domain', compute='_compute_account_tag_ids_domain')
    purchase_request_line_amount = fields.Float('Purchase Request Line Amount')
    product_budget_domain = fields.Char(compute="_compute_product_budget_domain")
    carry_over_amount = fields.Monetary('Carry Over Amount', compute='_compute_carry_over_amount')
    is_carry_over = fields.Boolean('Is Carry Over', default=False)
    parent_id = fields.Many2one('crossovered.budget', string="Budget Account Reference", related="purchase_budget_id.parent_id")


    def _compute_carry_over_amount(self):
        for line in self:
            final_carry_over_amount = 0

            budget_carry_over_lines = self.env['budget.purchase.carry.over.lines'].search([
                ('budget_purchase_carry_over_id.budget_purchase_id','=',line.purchase_budget_id.id),
                ('budget_purchase_carry_over_id.state','=','confirm'),
                ('product_budget','=',line.product_budget.id),
                ('group_product_id','=',line.group_product_id.id),
                ('product_id','=',line.product_id.id),
                ('budget_purchase_carry_over_id.new_budget_purchase_id.state','in',['confirm','validate','done']),
            ])
            for carry_line in budget_carry_over_lines:
                final_carry_over_amount -= carry_line.carry_over_amount

            # budget_carry_over_lines = self.env['budget.purchase.carry.over.lines'].search([
            #     ('budget_purchase_carry_over_id.new_budget_purchase_id','=',line.purchase_budget_id.id),
            #     ('budget_purchase_carry_over_id.state','=','confirm'),
            #     ('product_budget','=',line.product_budget.id),
            #     ('group_product_id','=',line.group_product_id.id),
            #     ('product_id','=',line.product_id.id),
            #     # ('date_from','=',line.date_from),
            #     # ('date_to','=',line.date_to),
            # ])
            # for carry_line in budget_carry_over_lines:
            #     final_carry_over_amount += carry_line.carry_over_amount

            line.carry_over_amount = final_carry_over_amount

    @api.constrains('group_product_id','product_id','date_from','date_to','account_tag_ids')
    def constrains_group_product_id(self):
        for req in self:
            purchase_budget_line = False
            if req.group_product_id:
                purchase_budget_line = self.search([('id','!=',req.id),('group_product_id','=',req.group_product_id.id),('date_from','<=',req.date_from),('date_to','>=',req.date_to),('account_tag_ids','in',req.account_tag_ids.ids),('purchase_budget_id.state1','=','validate'),('purchase_budget_id.is_parent_budget','=',False)], limit=1)
            elif req.product_id:
                purchase_budget_line = self.search([('id','!=',req.id),('product_id','=',req.product_id.id),('date_from','<=',req.date_from),('date_to','>=',req.date_to),('account_tag_ids','in',req.account_tag_ids.ids),('purchase_budget_id.state1','=','validate'),('purchase_budget_id.is_parent_budget','=',False)], limit=1)
            if purchase_budget_line and not req.purchase_budget_id.is_parent_budget:
                raise ValidationError("GoP/Product is already included in other purchase budget for this period!") 

    @api.depends('purchase_budget_id.parent_id', 'purchase_budget_id.parent_id.crossovered_budget_line', 'purchase_budget_id.parent_id.crossovered_budget_line.general_budget_id')
    def _compute_product_budget_domain(self):
        for rec in self:
            if rec.purchase_budget_id.parent_id and rec.purchase_budget_id.parent_id.crossovered_budget_line and rec.purchase_budget_id.parent_id.crossovered_budget_line.mapped('general_budget_id'):
                rec.product_budget_domain = json.dumps([('id', 'in', rec.purchase_budget_id.parent_id.crossovered_budget_line.mapped('general_budget_id').ids)])
            else:
                rec.product_budget_domain = json.dumps([('id', '=', 0)])

    @api.depends('purchase_budget_id.parent_budget_id', 'product_budget', 'purchase_budget_id.parent_id')
    def _compute_product_domain(self):
        if self.purchase_budget_id.parent_budget_id:
            group_product_ids = []
            product_ids = []

            for line in self.purchase_budget_id.parent_budget_id.purchase_budget_line:
                group_product_ids.append(line.group_product_id.id)
                product_ids.append(line.product_id.id)

            self.group_product_id_domain = json.dumps([('id','in',group_product_ids)])
            self.product_id_domain = json.dumps([('id','in',product_ids)])
        elif self.purchase_budget_id.parent_id:
            if self.product_budget:
                self.product_id_domain = json.dumps([('categ_id.property_stock_valuation_account_id', 'in', self.product_budget.account_ids.ids)])
                
                group_product_ids = []
                group_product = self.env['account.product.group'].search([])
                for gop in group_product:
                    for product in gop.product_ids:
                        if product.categ_id.property_stock_valuation_account_id.id in self.product_budget.account_ids.ids:
                            group_product_ids.append(gop.id)
                            break

                self.group_product_id_domain = json.dumps([('id','in',group_product_ids)])
            else:
                self.product_id_domain = json.dumps([])
                self.group_product_id_domain = json.dumps([])
        else:
            self.group_product_id_domain = json.dumps([])
            self.product_id_domain = json.dumps([('product_tmpl_id.group_product', '=', False)])

    @api.depends('purchase_budget_id.account_tag_ids')
    def _compute_account_tag_ids_domain(self):
        if self.purchase_budget_id:
            self.account_tag_ids_domain = json.dumps([('id','in',self.purchase_budget_id.account_tag_ids.ids)])

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            gop = []
            for line in self.purchase_budget_id.purchase_budget_line:
                gop.append(line.group_product_id.id)

            if self.product_id.group_product.id:
                if self.product_id.group_product.id in gop:
                    raise ValidationError("You can't choose this product that has included in Group of Product")

                # if self.product_id.group_product.id == line.group_product_id.id:
                #     raise ValidationError("You can't choose this product that has included in Group of Product")
                

    @api.depends('purchase_budget_id','group_product_id','account_tag_ids','date_to','date_from','product_id','planned_amount','practical_amount','reserve_amount','purchase_budget_id.child_budget_ids.total_planned_amount')
    def _compute_fields_practical(self):
        for record in self:
            record.reserve_amount = 0
            record.avail_amount = 0
            record.practical_amount = 0
            record.practical_amount_temp = 0
            # if not record.purchase_budget_id.is_parent_budget:
            if record.purchase_budget_id.state != 'done':
                if record.group_product_id and record.account_tag_ids:
                    purchase_ids= self.env['purchase.order.line'].search(
                        [
                            ('product_template_id.group_product','=',record.group_product_id.id),
                            # ('analytic_tag_ids','in',record.account_tag_ids.ids),
                            # ('date_planned','<=',record.date_to),
                            # ('date_planned','>=',record.date_from),
                            ('state','=','purchase'),
                            ('is_use_purchase_budget','=',True),
                        ]
                    )
                    total = 0                    
                    for purchase_id in purchase_ids:
                        is_correct = False
                        if purchase_id.order_id.from_purchase_request:
                            purchase_request = self.env['purchase.request'].search([('name','=',purchase_id.order_id.origin)], limit=1)
                            if purchase_request and purchase_request.request_date <= record.date_to and purchase_request.request_date >= record.date_from:
                                is_correct = True
                        else:
                            if purchase_id.date_planned.date() <= record.date_to and purchase_id.date_planned.date() >= record.date_from:
                                is_correct = True

                        if is_correct:
                            if any(item in record.account_tag_ids.ids for item in purchase_id.analytic_tag_ids.ids):
                                total += purchase_id.currency_id._convert((purchase_id.price_unit * purchase_id.product_qty), record.currency_id, record.company_id, purchase_id.date_planned)
                    record.practical_amount=total
                    record.practical_amount_temp=total

                    reserve_amount = 0
                    reserve_ids = self.env['purchase.request.line'].search(
                        [
                            ('request_id.request_date', '>=', record.date_from), ('request_id.request_date', '<=', record.date_to), 
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
                            reserve_amount += reserve_id.currency_id._convert(actual_amount, record.currency_id, record.company_id, reserve_id.date_start)
                    record.reserve_amount = reserve_amount
                    record.purchase_request_line_amount = reserve_amount
                elif record.product_id and record.account_tag_ids:
                    purchase_ids= self.env['purchase.order.line'].search(
                        [
                            ('product_template_id','=',record.product_id.product_tmpl_id.id),
                            # ('analytic_tag_ids','in',record.account_tag_ids.ids),
                            # ('date_planned','<=',record.date_to),
                            # ('date_planned','>=',record.date_from),
                            ('state','=','purchase'),
                            ('is_use_purchase_budget','=',True),
                        ]
                    )
                    total = 0                    
                    for purchase_id in purchase_ids:
                        is_correct = False
                        if purchase_id.order_id.from_purchase_request:
                            purchase_request = self.env['purchase.request'].search([('name','=',purchase_id.order_id.origin)], limit=1)
                            if purchase_request and purchase_request.request_date <= record.date_to and purchase_request.request_date >= record.date_from:
                                is_correct = True
                        else:
                            if purchase_id.date_planned.date() <= record.date_to and purchase_id.date_planned.date() >= record.date_from:
                                is_correct = True

                        if is_correct:
                            if any(item in record.account_tag_ids.ids for item in purchase_id.analytic_tag_ids.ids):
                                total += purchase_id.currency_id._convert((purchase_id.price_unit * purchase_id.product_qty), record.currency_id, record.company_id, purchase_id.date_planned)
                    record.practical_amount=total
                    record.practical_amount_temp=total

                    reserve_amount = 0
                    reserve_ids = self.env['purchase.request.line'].search(
                        [
                            ('request_id.request_date', '>=', record.date_from), ('request_id.request_date', '<=', record.date_to), 
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
                            reserve_amount += reserve_id.currency_id._convert(actual_amount, record.currency_id, record.company_id, reserve_id.date_start)
                    record.reserve_amount = reserve_amount
                    record.purchase_request_line_amount = reserve_amount
                else:
                    record.practical_amount=0

                # if record.purchase_budget_id.is_parent_budget:
                #     record.practical_amount = record.practical_amount_temp = reserve_amount = 0
                #     for child in record.purchase_budget_id.child_budget_ids:
                #         for line in child.purchase_budget_line:
                #             record.practical_amount += line.practical_amount
                #             record.practical_amount_temp += line.practical_amount
                #             record.reserve_amount += line.reserve_amount
            else:
                record.practical_amount = record.practical_amount_temp

            monthly_budget_line_ids = self.env['monthly.purchase.budget.line'].search([
                ('monthly_purchase_budget_id.budget_purchase_id','=',record.purchase_budget_id.id),
                ('group_product_id','=',record.group_product_id.id),
                ('product_id','=',record.product_id.id),
                ('account_tag_ids','in',record.account_tag_ids.ids),
                ('monthly_purchase_budget_id.date_from','>=',record.date_from),
                ('monthly_purchase_budget_id.date_to','<=',record.date_to),
                ('monthly_purchase_budget_id.state','!=','draft'),
            ])
            if monthly_budget_line_ids:
                record.reserve_amount = 0
                record.practical_amount = 0
                for line in monthly_budget_line_ids:
                    if line.monthly_purchase_budget_id.state == 'validate':
                        record.reserve_amount += line.avail_amount + line.reserve_amount
                        record.practical_amount += line.practical_amount
                    if line.monthly_purchase_budget_id.state == 'done':
                        record.practical_amount += line.practical_amount

            if record.purchase_budget_id.is_parent_budget:
                purchase_budget_line = self.search([
                    ('purchase_budget_id.parent_budget_id','=',record.purchase_budget_id.id),
                    ('group_product_id','=',record.group_product_id.id),
                    ('product_id','=',record.product_id.id),
                    # ('account_tag_ids','in',record.account_tag_ids.ids),
                    ('date_from','>=',record.date_from),
                    ('date_to','<=',record.date_to),
                    ('purchase_budget_id.state1','in',['validate']),
                ])
                if purchase_budget_line:
                    for child in purchase_budget_line:
                        #minus reserve amount from children monthly
                        # monthly_budget_line_ids = self.env['monthly.purchase.budget.line'].search([
                        #     ('monthly_purchase_budget_id.budget_purchase_id','=',child.purchase_budget_id.id),
                        #     ('group_product_id','=',child.group_product_id.id),
                        #     ('product_id','=',child.product_id.id),
                        #     ('account_tag_ids','in',child.account_tag_ids.ids),
                        #     ('monthly_purchase_budget_id.date_from','>=',child.date_from),
                        #     ('monthly_purchase_budget_id.date_to','<=',child.date_to),
                        #     ('monthly_purchase_budget_id.state','!=','draft'),
                        # ])
                        # if monthly_budget_line_ids:
                        #     record.reserve_amount += child.reserve_amount
                        # else:
                        #     record.reserve_amount -= child.reserve_amount
                        # record.reserve_amount += child.remaining_amount
                        record.practical_amount += child.practical_amount
                        record.reserve_amount -= child.purchase_request_line_amount
                        record.reserve_amount += child.planned_amount
                    record.reserve_amount -= record.practical_amount
                    
            record.practical_amount_temp = record.practical_amount
            record.avail_amount = record.planned_amount - record.practical_amount - record.reserve_amount

    # @api.onchange('practical_amount_temp')
    # def onchange_practical_amount_temp_1(self):
    #     for record in self:
    #         if record.purchase_budget_id.state != 'done':
    #             record.practical_amount = record.practical_amount_temp
    

    # @api.onchange('product_id','account_tag_ids','practical_amount','purchase_order_line_budget_id.price_subtotal')
    # def onchange_practical_amounts(self):
    #     for record in self:
    #         # record.practical_amount=0
    #         if record.product_id or record.account_tag_ids:
    #             purchase_ids= self.env['purchase.order.line'].search(
    #                 [
    #                     ('product_template_id','=',record.product_id.id),
    #                     ('analytic_tag_ids','in',record.account_tag_ids.ids),
    #                     ('date_planned','<=',record.date_to),
    #                     ('date_planned','>=',record.date_from)
    #                 ]
    #             )
    #             record.practical_amount=sum(purchase_ids.mapped('price_subtotal'))
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # overrides the default read_group in order to compute the computed fields manually for the group

        result = super(PurchaseBudgetLines, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                                orderby=orderby, lazy=lazy)
        fields_list = ['practical_amount', 'theoritical_amount', 'percentage']
        if any(x in fields for x in fields_list):
            for group_line in result:

                # initialise fields to compute to 0 if they are requested
                if 'practical_amount' in fields:
                    group_line['practical_amount'] = 0
                if 'theoritical_amount' in fields:
                    group_line['theoritical_amount'] = 0
                if 'percentage' in fields:
                    group_line['percentage'] = 0
                    group_line['practical_amount'] = 0
                    group_line['theoritical_amount'] = 0

                if group_line.get('__domain'):
                    all_budget_lines_that_compose_group = self.search(group_line['__domain'])
                else:
                    all_budget_lines_that_compose_group = self.search([])
                for budget_line_of_group in all_budget_lines_that_compose_group:
                    if 'practical_amount' in fields or 'percentage' in fields:
                        group_line['practical_amount'] += budget_line_of_group.practical_amount

                    if 'theoritical_amount' in fields or 'percentage' in fields:
                        group_line['theoritical_amount'] += budget_line_of_group.theoritical_amount

                    if 'percentage' in fields:
                        if group_line['theoritical_amount']:
                            # use a weighted average
                            group_line['percentage'] = float(
                                (group_line['practical_amount'] or 0.0) / group_line['theoritical_amount']) * 100

        return result

    def _is_above_budget(self):
        for line in self:
            if line.theoritical_amount >= 0:
                line.is_above_budget = line.practical_amount > line.theoritical_amount
            else:
                line.is_above_budget = line.practical_amount < line.theoritical_amount

    def _compute_line_name(self):
        # just in case someone opens the budget line in form view
        computed_name = self.purchase_budget_id.name
        if self.product_budget:
            computed_name += ' - ' + self.product_budget.name
        if self.analytic_account_id:
            computed_name += ' - ' + self.analytic_account_id.name
        self.name = computed_name

    def _compute_practical_amount(self):
#        purchase_request_query = """SELECT COALESCE(SUM(product_qty*estimated_cost),0) 
#                                FROM purchase_request_line
#                                WHERE product_id = %s
#                                AND date_required <= %s
#                                AND date_required >= %s#""" 
        # purchase_order_query = """SELECT COALESCE(SUM(price_subtotal),0) 
        #                         FROM purchase_order_line
        #                         WHERE product_id = %s
        #                         AND date_planned <= %s
        #                         AND date_planned >= %s"""                        
        for line in self:
            acc_ids = line.product_budget.account_ids.ids
            date_to = line.date_to
            date_from = line.date_from
            if line.account_tag_ids.id:
                analytic_line_obj = self.env['account.analytic.line']
                domain = [('account_id', '=', line.account_tag_ids.id),
                          ('product_id', '=', line.product_id.id),
                          ('date', '>=', date_from),
                          ('date', '<=', date_to),
                          ]
                if acc_ids:
                    domain += [('general_account_id', 'in', acc_ids)]

                where_query = analytic_line_obj._where_calc(domain)
                analytic_line_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT SUM(amount) from " + from_clause + " where " + where_clause

            else:
                aml_obj = self.env['account.move.line']
                domain = [('account_id', 'in', line.product_budget.account_ids.ids),
                          ('product_id', '=', line.product_id.id),
                          ('date', '>=', date_from),
                          ('date', '<=', date_to),
                          ('move_id.is_from_receiving_note','=',False),
                          ]
                where_query = aml_obj._where_calc(domain)
                aml_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT sum(credit)-sum(debit) from " + from_clause + " where " + where_clause

            self.env.cr.execute(select, where_clause_params)# practical_amount = self.env.cr.fetchone()[0] or 0.0
            practical_amount = self.env.cr.fetchone()[0] or 0.0
#            self.env.cr.execute(purchase_request_query, (line.product_id.id,date_to,date_from))
#            purchase_request_budget = self.env.cr.fetchone()[0] or 0.0
            # self.env.cr.execute(purchase_order_query, (line.product_id.id,date_to,date_from))
            # purchase_order_budget = self.env.cr.fetchone()[0] or 0.0
            
            # if purchase_order_budget:
            #     practical_amount = purchase_order_budget
            line.practical_amount = practical_amount or 0

    eer = fields.Char('field_name')      
    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.eer = self.product_id.id

    @api.depends('paid_date', 'planned_amount', 'date_from', 'date_to')
    def _compute_theoritical_amount(self):
        # beware: 'today' variable is mocked in the python tests and thus, its implementation matter
        today = fields.Date.today()
        for line in self:
            contains_false = any(not value for value in [line.date_to, line.date_from])
            if contains_false:
                raise ValidationError(_('Cannot continue operation because period not filled!'))

            if line.paid_date:
                if today <= line.paid_date:
                    theo_amt = 0.00
                else:
                    theo_amt = line.planned_amount
            else:
                line_timedelta = line.date_to - (line.date_from - timedelta(days=1))
                elapsed_timedelta = today - (line.date_from - timedelta(days=1))
                # elapsed_timedelta = today - line.date_from

                if elapsed_timedelta.days < 0:
                    # If the budget line has not started yet, theoretical amount should be zero
                    theo_amt = 0.00
                elif line_timedelta.days > 0 and today < line.date_to:
                    # If today is between the budget line date_from and date_to
                        theo_amt = (elapsed_timedelta / line_timedelta) * line.planned_amount
                        # print('====TEST',line_timedelta)
                        # print('====TEST',elapsed_timedelta)
                        # print('====TEST',theo_amt)
                else:
                    theo_amt = line.planned_amount
            line.theoritical_amount = theo_amt
            # sup = super(PurchaseBudgetLines,self)
            # test = self.env['purchase.order'].search([('order_line.product_id.id','=',sup.product_id.id)])
            # print(test)

    @api.depends('practical_amount', 'theoritical_amount')
    def _compute_percentage(self):
        for line in self:
            if line.theoritical_amount != 0.00:
                if line.practical_amount == 0:
                    line.percentage = 0.00
                else:
                    line.percentage = float((line.practical_amount or 0.0) / line.theoritical_amount)
            else:
                line.percentage = 0.00
 
    def action_open_purchase_order_lines(self):
        action = self.env['ir.actions.act_window']._for_xml_id('equip3_purchase_operation.product_purchase_orders_line')

        purchase_ids = []
        date_from = self.date_from
        date_to = self.date_to

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
        
        # action['domain'] = [('date_planned','>=',self.date_from),('date_planned','<=',self.date_to),('state','=','purchase'),('is_use_purchase_budget','=',True)]

        # if self.group_product_id:
        #     action['domain'] += [('product_template_id.group_product', '=', self.group_product_id.id)]
        # elif self.product_id:
        #     action['domain'] += [('product_template_id', '=', self.product_id.product_tmpl_id.id)]
        
        # if self.account_tag_ids.ids:
        #     action['domain'] += [('analytic_tag_ids','in',self.account_tag_ids.ids)]

        return action

    def action_open_purchase_request_lines(self):
        action = self.env['ir.actions.act_window']._for_xml_id('purchase_request.purchase_request_line_form_action')
        action['domain'] = [('request_id.request_date','>=',self.date_from),('request_id.request_date','<=',self.date_to),('request_id.pr_state','=','purchase_request'),('is_use_purchase_budget','=',True)]

        if self.group_product_id:
            action['domain'] += [('product_id.product_tmpl_id.group_product', '=', self.group_product_id.id)]
        elif self.product_id:
            action['domain'] += [('product_id', '=', self.product_id.id)]
        
        if self.account_tag_ids.ids:
            action['domain'] += [('analytic_account_group_ids','in',self.account_tag_ids.ids)]

        return action
 

    def action_open_budget_entries(self):
        if self.analytic_account_id:
            # if there is an analytic account, then the analytic items are loaded
            action = self.env['ir.actions.act_window']._for_xml_id('analytic.account_analytic_line_action_entries')
            action['domain'] = [('account_id', '=', self.analytic_account_id.id),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
            if self.product_budget:
                action['domain'] += [('general_account_id', 'in', self.product_budget.account_ids.ids)]
        else:
            # otherwise the journal entries booked on the accounts of the budgetary postition are opened
            action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
            action['domain'] = [('account_id', 'in',
                                 self.product_budget.account_ids.ids),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
        return action

    @api.constrains('date_from', 'date_to')
    def _line_dates_between_budget_dates(self):
        for rec in self:
            budget_date_from = rec.purchase_budget_id.date_from
            budget_date_to = rec.purchase_budget_id.date_to
            if rec.date_from:
                date_from = rec.date_from
                if date_from < budget_date_from or date_from > budget_date_to:
                    raise ValidationError(
                        _('"Start Date" of the budget line should be included in the Period of the budget'))
            if rec.date_to:
                date_to = rec.date_to
                if date_to < budget_date_from or date_to > budget_date_to:
                    raise ValidationError(
                        _('"End Date" of the budget line should be included in the Period of the budget'))
    
    @api.depends('planned_amount', 'practical_amount')
    def _compute_remaining_amount(self):
        for line in self:
            line.remaining_amount = line.planned_amount - line.practical_amount + line.carry_over_amount
            line.avail_amount = line.remaining_amount
            
    @api.constrains('planned_amount')
    def _check_amount(self):
        for line in self:
            if line.purchase_budget_id.parent_budget_id:
                purchase_budget_line = self.search([
                    ('purchase_budget_id','=',line.purchase_budget_id.parent_budget_id.id),
                    ('group_product_id','=',line.group_product_id.id),
                    ('product_id','=',line.product_id.id),
                    # ('account_tag_ids','in',line.account_tag_ids.ids),
                    ('date_from','<=',line.date_from),
                    ('date_to','>=',line.date_to),
                ])

                if purchase_budget_line and line.planned_amount > purchase_budget_line.planned_amount:
                    raise ValidationError(_('You cannot allocate more than the parent budget planned amount.'))

                if purchase_budget_line and line.planned_amount > purchase_budget_line.avail_amount:
                    raise ValidationError(_('Planned Amount cannot bigger than Available to Reserve amount in Parent Budget!'))

            if line.planned_amount < 0:
                raise ValidationError(_('Planned Amount cannot be minus!'))

            carry_amount = 0
            for carry_line in line.purchase_budget_id.budget_purchase_carry_in_line_ids:
                if line.group_product_id.id == carry_line.group_product_id.id and line.product_id.id == carry_line.product_id.id and line.product_budget.id == carry_line.product_budget.id:
                    carry_amount += carry_line.carry_over_amount
            if carry_amount > 0:
                if line.planned_amount < carry_amount:
                    raise ValidationError(_('Planned amount cannot be less than carry over amount! %s' % f'{carry_amount:,}'))

    def unlink(self):
        for record in self:
            if record.is_carry_over:
                raise ValidationError(_('Cannot delete carry over lines!'))
        return super(PurchaseBudgetLines, self).unlink()