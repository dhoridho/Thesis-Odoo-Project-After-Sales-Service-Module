# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import ValidationError
import pytz
from odoo import tools
import requests
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

headers = {'content-type': 'application/json'}

def _default_get_requester(self):
    return self.env.user.id

class BudgetChangeReq(models.Model):
    _name = 'budget.change.req'
    _description = 'Budget Change Request'
    _inherit = ['mail.thread']

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

    name = fields.Char(string="Number", readonly=True, default='/', copy=False)
    requested_id = fields.Many2one('res.users', string='Requester', default=lambda self: self.env.user, required=True)
    budget_std_id = fields.Many2one('crossovered.budget', string='Budget', required=True, domain="[('state','=','validate')]")
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    budget_line = fields.One2many('budget.change.req.line', 'budget_change_req_id', string="Budget Line")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('rejected', 'Rejected'),
        ('approved', 'Approved'),
        ('confirm', 'Confirm')
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)
    approval_matrix = fields.Many2one('approval.matrix.accounting', string="Approval Matrix",
                                      compute='_get_approval_matrix', store=True)

    is_allowed_to_approval_matrix = fields.Boolean(string="Is Allowed Approval Matrix",
                                                   compute='_get_approve_status_from_config')
    is_allowed_to_wa_notification = fields.Boolean(string="Is Allowed WA Notification", compute='_get_approve_status_from_config')
    approved_matrix_ids = fields.One2many('approval.matrix.accounting.lines', 'account_budget_request_id',
                                          string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.accounting.lines', string='Approval Matrix Line',
                                              compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company, readonly=True)
    # branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.user.branch_id.id, store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, tracking=True, related="company_id.currency_id")
    request_partner_id = fields.Many2one('res.partner', string="Requested Partner")
    state1 = fields.Selection(related="state", tracking=False)
    state2 = fields.Selection(related="state", tracking=False)
    is_parent_budget = fields.Boolean(string="Is Parent Budget")
    parent_id = fields.Many2one('crossovered.budget', 'Parent Budget')
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Groups")
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
    

    @api.depends('budget_line', 'budget_line.new_amount', 'branch_id')
    def _get_approval_matrix(self):
        self._get_approve_status_from_config()
        for record in self:
            total_amount = sum(record.budget_line.mapped('new_amount')) - sum(record.budget_line.mapped('planned_amount'))
            matrix_id = self.env['approval.matrix.accounting'].search([
                ('approval_matrix_type', '=', 'budget_change_request_approval'),
                ('company_id', '=', record.company_id.id),
                ('branch_id', '=', record.branch_id.id),
                ('min_amount', '<=', total_amount),
                ('max_amount', '>=', total_amount),
            ], limit=1, order="id desc")
            record.approval_matrix = matrix_id and matrix_id.id or False
            record._compute_approving_matrix_lines()

    @api.depends('is_allowed_to_approval_matrix')
    def _get_approve_status_from_config(self):
        for record in self:
            res_user = self.env['res.users'].search([('id', '=', self._uid)])
            # record.is_allowed_to_approval_matrix = False
            # is_budget_change_req_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_budget_change_req_approval_matrix', False)
            # if is_budget_change_req_approval_matrix:
            #     record.is_allowed_to_approval_matrix = True
            record.is_allowed_to_approval_matrix = self.env['accounting.config.settings'].search([], limit=1).is_allow_budget_change_req_approval_matrix
            record.is_allowed_to_wa_notification = self.env['accounting.config.settings'].search([], limit=1).is_allow_budget_change_req_wa_notification

    def _get_approve_button(self):
        wa_sender = waParam()
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

    def _send_wa_reject_budget_change_req(self, submitter, phone_num, created_date, approver = False, reason = False):
        wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_rejection_budget_change_req_1')
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

    
    def _send_wa_approval_budget_change_req(self, approver, phone_num, created_date, submitter):
        wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_approval_budget_change_req_1')
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
            action_id = self.env.ref('equip3_accounting_budget.act_budget_change_req_view')
            template_id = self.env.ref('equip3_accounting_budget.email_template_application_for_budget_change_request_approval')
            template_id_submitter = self.env.ref('equip3_accounting_budget.email_template_approval_of_budget_change_request')
            
            # wa_template_id = self.env.ref('equip3_accounting_budget.wa_template_request_for_approval_budget_change_request')
            # wa_template_id_submitter = self.env.ref('equip3_accounting_budget.wa_template_approval_of_budget_change_request')
 
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=budget.change.req'
            created_date = record.create_date.date()
            if record.is_approve_button and record.approval_matrix_line_id:
                currency = ''
                new_amount = sum(record.budget_line.mapped('new_amount'))
                if record.company_id.currency_id.position == 'before':
                    currency = record.company_id.currency_id.symbol + str(new_amount)
                else:
                    currency = str(new_amount) + ' ' + record.company_id.currency_id.symbol
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
                                approver = next_approval_matrix_line_id[0].user_ids
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : approving_matrix_line_user.partner_id.email,
                                    'approver_name' : approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter' : self.env.user.name,
                                    'url' : url,
                                    "create_date": record.create_date.date(),
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                                if self.is_allowed_to_wa_notification:
                                    record._send_wa_approval_budget_change_req(approver, phone_num, created_date, self.env.user.name)
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
                                    "create_date":record.create_date.date(),
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                                if self.is_allowed_to_wa_notification:
                                    record._send_wa_approval_budget_change_req(approver, phone_num, created_date, self.env.user.name)
                                # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)

            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                record.action_for_approved()
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.request_partner_id.email,
                    'approver_name' : record.name,
                    'date': date.today(),
                    'create_date': record.create_date.date(),
                    'submitter' : self.env.user.name,
                    'url' : url,
                }
                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                phone_num = str(record.request_partner_id.mobile) or str(record.request_partner_id.phone)
                if self.is_allowed_to_wa_notification:
                    record._send_wa_approval_budget_change_req(record.request_partner_id, phone_num, created_date, self.env.user.name)
                # record._send_whatsapp_message_approval_submitter(wa_template_id_submitter, record.request_partner_id.name, phone_num,record.create_date.date())

    def check_duplicate_budget(self):
        for record in self:
            existing_budget_ids = self.env['crossovered.budget'].browse([])
            if self.is_parent_budget and not self.parent_id:
                existing_budget_ids = self.env['crossovered.budget'].search([
                    '|',
                    '&', ('date_from', '<', record.date_to), ('date_to', '>', record.date_from),  # Overlapping condition
                    '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_from), 
                    ('crossovered_budget_line.general_budget_id', 'in', record.budget_line.mapped('budgetary_position_id').ids), # Including exact match
                    ('id', '!=', record.budget_std_id.id),
                    ('state', '=', 'validate'),
                    ('parent_id', '!=', record.budget_std_id.id),
                ])
            elif self.is_parent_budget and self.parent_id:
                existing_budget_ids = self.env['crossovered.budget'].search([
                    '|',
                    '&', ('date_from', '<', record.date_to), ('date_to', '>', record.date_from),  # Overlapping condition
                    '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_from),  # Including exact match
                    ('crossovered_budget_line.general_budget_id', 'in', record.budget_line.mapped('budgetary_position_id').ids),
                    ('id', '!=', record.budget_std_id.id),
                    ('parent_id', '=', record.parent_id.id),
                    ('state', '=', 'validate'),
                    ('is_parent_budget', '=', True),  # Ensure we're only considering parent budgets
                    ('parent_id', '!=', record.budget_std_id.id),
                ])
            elif not self.is_parent_budget and self.parent_id:
                existing_budget_ids = self.env['crossovered.budget'].search([
                    '|',
                    '&', ('date_from', '<', record.date_to), ('date_to', '>', record.date_from),  # Overlapping condition
                    '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_from),  # Including exact match
                    ('account_tag_ids', 'in', record.account_tag_ids.ids),
                    ('crossovered_budget_line.general_budget_id', 'in', record.budget_line.mapped('budgetary_position_id').ids),
                    ('id', '!=', record.budget_std_id.id),
                    ('state', '=', 'validate'),
                    ('parent_id', '=', record.parent_id.id),
                    ('is_parent_budget','=',False),
                ])
            else:
                existing_budget_ids = self.env['crossovered.budget'].search([
                    '|',
                    '&', ('date_from', '<', record.date_to), ('date_to', '>', record.date_from),  # Overlapping condition
                    '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_from),  # Including exact match
                    '|', ('account_tag_ids', 'in', record.account_tag_ids.ids),
                    ('account_tag_ids', '=', False),
                    ('crossovered_budget_line.general_budget_id', 'in', record.budget_line.mapped('budgetary_position_id').ids),
                    ('id', '!=', record.budget_std_id.id),
                    ('state', '=', 'validate'),
                    ('is_parent_budget','=',False),
                ])

            if existing_budget_ids and not self.is_parent_budget:
                conflicting_budget_names = ', '.join(existing_budget_ids.mapped('name'))
                raise ValidationError('You cannot create budget, because it already exists or inside period of budget with names: %s.' % conflicting_budget_names)

            if record.parent_id:
                if record.date_from < record.parent_id.date_from or record.date_to > record.parent_id.date_to:
                    raise ValidationError('The date is out of the Parent Budget period.')

            if record.date_to < record.date_from:
                raise ValidationError('End date cannot before the start date.')

    def _send_wa_request_for_approval_budget_change_req(self, approver, phone_num, currency, url, submitter):
        wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_request_approval_budget_change_req_1')
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
            record.check_new_amount()
            record.check_duplicate_budget()
            action_id = self.env.ref('equip3_accounting_budget.act_budget_change_req_view')
            template_id = self.env.ref('equip3_accounting_budget.email_template_application_for_budget_change_request_approval')
            # wa_template_id = self.env.ref('equip3_accounting_budget.wa_template_request_for_approval_budget_change_request')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=budget.change.req'
            currency = ''
            new_amount = sum(record.budget_line.mapped('new_amount'))
            if record.company_id.currency_id.position == 'before':
                currency = record.company_id.currency_id.symbol + str(new_amount)
            else:
                currency = str(new_amount) + ' ' + record.company_id.currency_id.symbol
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
                        'new_amount': new_amount,
                        "create_date": record.date,                      
                        "currency": currency,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                    if self.is_allowed_to_wa_notification:
                    # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)
                        record._send_wa_request_for_approval_budget_change_req(approver, phone_num, currency, url, self.env.user.name)

            else:
                approver = record.approved_matrix_ids[0].user_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : approver.partner_id.email,
                    'approver_name' : approver.name,
                    'date': date.today(),
                    'submitter' : self.env.user.name,
                    'url' : url,
                    'new_amount': new_amount,
                    "create_date": record.date, 
                    "currency": currency,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                if self.is_allowed_to_wa_notification:
                # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)
                    record._send_wa_request_for_approval_budget_change_req(approver, phone_num, currency, url, self.env.user.name)

            record.write({'state': 'to_approve'})
            
    def action_confirm(self):
        for record in self:
            record.check_new_amount()
            record.write({'state': 'confirm'})

    def action_for_approved(self):
        for record in self:
            record.write({'state': 'confirm'})

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Account Budget Request Change',
            'res_model': 'budget.change.req.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.onchange('budget_std_id')
    def _onchange_budget_std_id(self):
        budget_line_list = [(5, 0, 0)]
        for req in self:
            req.write({
                'is_parent_budget': req.budget_std_id.is_parent_budget,
                'parent_id': req.budget_std_id.parent_id.id,
                'account_tag_ids': req.budget_std_id.account_tag_ids.ids,
                'date_from': req.budget_std_id.date_from,
                'date_to': req.budget_std_id.date_to,
            })
            for line in req.budget_std_id.crossovered_budget_line:
                budget_line_list.append((0, 0, {'budgetary_position_id': line.general_budget_id.id,
                                                'account_tag_ids': line.account_tag_ids.ids,
                                                'date_from': line.date_from,
                                                'date_to': line.date_to,
                                                'planned_amount': line.budget_amount,
                                                'new_amount': line.budget_amount,
                                                }))
            req.budget_line = budget_line_list

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

    @api.model
    def create(self, vals):
        # vals['name'] = self.env['ir.sequence'].next_by_code('budget.change.req')
        result = super(BudgetChangeReq, self).create(vals)
        # for req in result:
        #     for line in req.budget_line:
        #         crossovered_budget_lines = self.env['crossovered.budget.lines'].search(
        #             [('general_budget_id', '=', line.budgetary_position_id.id),
        #              ('crossovered_budget_id', '=', req.budget_std_id.id)])
        #         for budget_line in crossovered_budget_lines:
        #             budget_line.write({'planned_amount': line.new_amount})

        return result

    def write(self, vals):
        result = super(BudgetChangeReq, self).write(vals)
        for req in self:
            if vals.get('state') and req.name == '/':
                req.name = self.env['ir.sequence'].next_by_code('budget.change.req')
            if vals.get('state') in ['to_approve','confirm']:
                if req.is_parent_budget:
                    for line in req.budget_line:
                        crossovered_budget_lines = self.env['crossovered.budget.lines'].search(
                            [('general_budget_id', '=', line.budgetary_position_id.id),
                             ('crossovered_budget_id', '=', req.budget_std_id.id)])
                        for budget_line in crossovered_budget_lines:
                            if line.new_amount < budget_line.reserve_amount:
                                raise ValidationError("%s is parent budget. You cannot allocate less than the child account amount." % req.budget_std_id.name)

                for line in req.budget_line:
                    if line.new_amount <= 0:
                        raise ValidationError("New budget amount must be greater than 0.")

                if not req.budget_std_id.is_parent_budget:
                    for line in req.budget_line:
                        crossovered_budget_lines = self.env['crossovered.budget.lines'].search(
                            [('general_budget_id', '=', line.budgetary_position_id.id),
                             ('crossovered_budget_id', '=', req.budget_std_id.id)])
                        if line.new_amount < (sum(crossovered_budget_lines.mapped('child_purchase_amount')) + sum(crossovered_budget_lines.mapped('reserve_amount_2')) + sum(crossovered_budget_lines.mapped('practical_budget_amount'))):
                            raise ValidationError("%s has been reserved and used. You cannot change less than child purchase, account reserved and realized amount." % req.budget_std_id.name)

            if vals.get('state') in ['approved','confirm']:
                req.budget_std_id.write({
                    'is_parent_budget': req.is_parent_budget,
                    'parent_id': req.parent_id.id,
                    'account_tag_ids': req.account_tag_ids.ids,
                    'date_from': req.date_from,
                    'date_to': req.date_to,
                })
                for line in req.budget_line:
                    if req.budget_std_id.is_parent_budget:
                        crossovered_budget_lines = self.env['crossovered.budget.lines'].search(
                            [('general_budget_id', '=', line.budgetary_position_id.id),
                             ('crossovered_budget_id', '=', req.budget_std_id.id)])
                    else:
                        crossovered_budget_lines = self.env['crossovered.budget.lines'].search(
                            [('general_budget_id', '=', line.budgetary_position_id.id),
                             ('crossovered_budget_id', '=', req.budget_std_id.id),
                             ('account_tag_ids','in',line.account_tag_ids.ids)])
                    for budget_line in crossovered_budget_lines:
                        budget_line.write({
                            'change_amount': line.new_amount - line.planned_amount,
                            'account_tag_ids': line.account_tag_ids.ids,
                            'date_from': line.date_from,
                            'date_to': line.date_to,
                        })
                    if not crossovered_budget_lines:
                        self.env['crossovered.budget.lines'].create({
                            'crossovered_budget_id': req.budget_std_id.id,
                            'general_budget_id': line.budgetary_position_id.id,
                            'account_tag_ids': line.account_tag_ids.ids,
                            'date_from': line.date_from,
                            'date_to': line.date_to,
                            'planned_amount': line.new_amount,
                        })

                #if have duplicate line, combine the line
                if req.budget_std_id.is_parent_budget:
                    for line in req.budget_std_id.crossovered_budget_line:
                        try:
                            crossovered_budget_lines = self.env['crossovered.budget.lines'].search(
                                [('general_budget_id', '=', line.general_budget_id.id),
                                 ('crossovered_budget_id', '=', req.budget_std_id.id),
                                 ('id', '!=', line.id)])
                            for budget_line in crossovered_budget_lines:
                                line.planned_amount += budget_line.budget_amount
                                budget_line.unlink()
                        except:
                            pass

            if vals.get('state') and req.state not in ['approved','confirm']:
                req.check_backdate_period(req.date_to)

        return result

    def check_new_amount(self):
        if self.budget_std_id.parent_id:
            total_budget_amount_change = 0
            for line in self.budget_line:
                budget_crq = self.env['crossovered.budget'].search([('id', '=', line.budget_change_req_id.budget_std_id.id)])
                if (budget_crq.is_parent_budget and budget_crq.parent_id) or (not budget_crq.is_parent_budget and budget_crq.parent_id):
                    # budget_amount = budget_crq.parent_id.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == line.budgetary_position_id.id).budget_amount
                    # reserve_amount = budget_crq.parent_id.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == line.budgetary_position_id.id).reserve_amount
                    parent_budget_line = budget_crq.parent_id.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == line.budgetary_position_id.id)
                    # transfer_amount = sum(budget_crq.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == line.budgetary_position_id.id).mapped('transfer_amount'))
                    # parent_budget_amount = budget_amount - reserve_amount
                    # subtotal_new_amount = sum(self.budget_line.mapped('new_amount'))
                    budget_amount_change = line.new_amount - line.planned_amount

                    # if budget_amount_change > parent_budget_amount:
                        # raise ValidationError("%s is child budget. You cannot allocate more than parent budget amount" % budget_crq.name)
                    total_budget_amount_change += budget_amount_change
                    if parent_budget_line and total_budget_amount_change > parent_budget_line.available_to_child_amount:
                        raise ValidationError("%s is child budget. You cannot allocate more than the parent budget amount." % budget_crq.name)

                elif line.new_amount <= 0:
                    raise ValidationError("New amount must be greater than 0.")

    @api.onchange('is_parent_budget') 
    def _onchange_is_parent_budget(self):
        for budget in self:
            if budget.is_parent_budget:
                budget.account_tag_ids = False
                for line in budget.budget_line:
                    line.account_tag_ids = False

    @api.onchange('date_from','date_to') 
    def _onchange_budget_date(self):
        for line in self.budget_line:
            line.date_from = line.budget_change_req_id.date_from
            line.date_to = line.budget_change_req_id.date_to

    def check_backdate_period(self, date_to):
        today = fields.Date.today()
        if date_to and today > date_to and self.state != 'done':
            raise ValidationError('Cannot create budget in backdate periods')

    @api.constrains('date_from', 'date_to')
    def _line_dates_between_budget_dates(self):
        for rec in self:
            if rec.date_to < rec.date_from:
                raise ValidationError('End date cannot before the start date.')

    @api.onchange('account_tag_ids')
    def _onchange_account_tag_ids(self):
        for line in self.budget_line:
            line.account_tag_ids = line.budget_change_req_id.account_tag_ids.ids


class BudgetChangeReqLine(models.Model):
    _name = 'budget.change.req.line'
    _description = 'Budget Change Request Line'

    budget_change_req_id = fields.Many2one('budget.change.req', string='Budget Change Request')
    budgetary_position_id = fields.Many2one('account.budget.post', 'Budgetary Position', required=True)
    planned_amount = fields.Float('Current Budget Amount')
    new_amount = fields.Float('New Budget Amount', required=True)
    budget_std_id = fields.Many2one('crossovered.budget', string="Budget Name", related="budget_change_req_id.budget_std_id")
    budget_change_req_name = fields.Char('Number', related="budget_change_req_id.name")
    budget_change_req_date = fields.Date(string='Date', related="budget_change_req_id.date")
    currency_id = fields.Many2one('res.currency', related="budget_change_req_id.currency_id")
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Groups")
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')


class ApprovalMatrixAccountingLines(models.Model):
    _inherit = "approval.matrix.accounting.lines"

    account_budget_request_id = fields.Many2one('budget.change.req', string='Account Request Budget')
