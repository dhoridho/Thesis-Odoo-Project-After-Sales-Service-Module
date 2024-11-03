
from odoo import api, fields, models, _
from datetime import datetime, date
import pytz
from odoo import tools
import requests
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
import json
from odoo.exceptions import ValidationError


headers = {'content-type': 'application/json'}

class PurchaseChangeRequest(models.Model):
    _name = "purchase.change.request"
    _description = 'Purchase Change Request'

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
        tracking=True,
        readonly=False)

    name = fields.Char(string="Name", readonly=True)
    requested_id = fields.Many2one('res.users', string="Requester",default=lambda self:self.env.user.id)
    budget_std_id = fields.Many2one('budget.purchase', string="Purchase Budget")
    date = fields.Date(string="Date",default=datetime.now())
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)
    # branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.user.branch_id.id)
    
    pur_change_req_ids = fields.One2many('purchase.change.request.line', 'purchase_chn_req_id', string="purchase")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirm', 'Confirm'),
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)
    state1 = fields.Selection(related="state", tracking=False)
    state2 = fields.Selection(related="state", tracking=False)
    budget_line = fields.One2many('budget.change.req.line', 'budget_change_req_id', string="Budget Line")
    approval_matrix = fields.Many2one('approval.matrix.accounting', string="Approval Matrix",
                                      compute='_get_approval_matrix', store=True)

    is_allowed_to_approval_matrix = fields.Boolean(string="Is Allowed Approval Matrix",
                                                   compute='_get_approve_status_from_config')
    is_allowed_to_wa_notification = fields.Boolean(string="Is Allowed WA Notification",
                                                   compute='_get_approve_status_from_config')
    approved_matrix_ids = fields.One2many('approval.matrix.accounting.lines', 'account_budget_req_id',
                                          string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.accounting.lines', string='Approval Matrix Line',
                                              compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, tracking=True)
    request_partner_id = fields.Many2one('res.partner', string="Requested Partner")
    parent_id = fields.Many2one('crossovered.budget', 'Budget Account Reference', related='budget_std_id.parent_id')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    is_parent_budget = fields.Boolean(string="Is Parent Budget", default=False)
    parent_budget_id = fields.Many2one('budget.purchase', 'Parent Budget', index=True, ondelete='cascade')
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    account_tag_ids_domain = fields.Char(string='Analytic Group Domain', compute='_compute_account_tag_ids_domain')


    @api.depends('parent_budget_id.account_tag_ids','parent_id.account_tag_ids')
    def _compute_account_tag_ids_domain(self):
        for rec in self:
            account_tag_ids_to_domain = []
            if rec.parent_id and rec.parent_id.account_tag_ids:
                account_tag_ids_to_domain.extend(rec.parent_id.account_tag_ids.ids)
            if rec.parent_budget_id and rec.parent_id.account_tag_ids:
                account_tag_ids_to_domain.extend(rec.parent_budget_id.account_tag_ids.ids)
            if account_tag_ids_to_domain:
                rec.account_tag_ids_domain = json.dumps([('id','in', account_tag_ids_to_domain)])
            else:
                rec.account_tag_ids_domain = json.dumps([])

    @api.depends('pur_change_req_ids', 'pur_change_req_ids.new_amount', 'branch_id')
    def _get_approval_matrix(self):
        self._get_approve_status_from_config()
        for record in self:
            total_amount = sum(record.pur_change_req_ids.mapped('new_amount')) - sum(record.pur_change_req_ids.mapped('planned_amount'))
            matrix_id = self.env['approval.matrix.accounting'].search([
                ('approval_matrix_type', '=', 'purchase_budget_change_request_approval'),
                ('company_id', '=', record.company_id.id),
                ('branch_id', '=', record.branch_id.id),
                ('min_amount', '<=', total_amount),
                ('max_amount', '>=', total_amount),
            ], limit=1, order="id desc")
            record.approval_matrix = matrix_id and matrix_id.id or False
            record._compute_approving_matrix_lines()
    
    @api.onchange('requested_id')
    def _onchange_requested_id(self):
        self._get_approve_status_from_config()

    def _get_approve_status_from_config(self):
        for record in self:
            # record.is_allowed_to_approval_matrix = False
            # is_purchase_budget_change_req_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_purchase_budget_change_req_approval_matrix', False)
            # if is_purchase_budget_change_req_approval_matrix:
            #     record.is_allowed_to_approval_matrix = True
            record.is_allowed_to_approval_matrix = self.env['accounting.config.settings'].search([], limit=1).is_allow_purchase_budget_change_req_approval_matrix
            record.is_allowed_to_wa_notification = self.env['accounting.config.settings'].search([], limit=1).is_allow_purchase_budget_change_req_wa_notification

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

    def _send_wa_reject_purchase_budget_change_req(self, submitter, phone_num, created_date, approver = False, reason = False):
        wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_rejection_purchase_budget_change_req_1')
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
    
    def _send_wa_approval_purchase_budget_change_req(self, approver, phone_num, created_date, submitter):
        wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_approval_purchase_budget_change_req_1')
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
            action_id = self.env.ref('equip3_accounting_budget.action_account_purchase_change_request')
            template_id = self.env.ref('equip3_accounting_budget.email_template_application_for_purchase_budget_change_request_approval')
            template_id_submitter = self.env.ref('equip3_accounting_budget.email_template_approval_of_purchase_budget_change_request')
            
            # wa_template_id = self.env.ref('equip3_accounting_budget.wa_template_request_for_approval_purchase_budget_change_request')
            # wa_template_id_submitter = self.env.ref('equip3_accounting_budget.wa_template_approval_of_purchase_budget_change_request')
 
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=purchase.change.request'
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
                                approver = approving_matrix_line_user
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
                                if record.is_allowed_to_wa_notification:
                                    record._send_wa_approval_purchase_budget_change_req(approver, phone_num, created_date, self.env.user.name)
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
                                if record.is_allowed_to_wa_notification:
                                    record._send_wa_approval_purchase_budget_change_req(approver, phone_num, created_date, self.env.user.name)
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
                if record.is_allowed_to_wa_notification:
                    record._send_wa_approval_purchase_budget_change_req(record.request_partner_id, phone_num, created_date, self.env.user.name)
                # record._send_whatsapp_message_approval_submitter(wa_template_id_submitter, record.request_partner_id.name, phone_num,record.create_date.date())
       
    def action_confirm(self):
        for record in self:            
            record.write({'state': 'confirm'})
            # for line in record.pur_change_req_ids:
            #     line._change_parent_planned_amount()

    def _send_wa_request_for_approval_purchase_budget_change_req(self, approver, phone_num, currency, url, submitter):
            wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_request_approval_purchase_budget_change_req_1')
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
            record.write({'state': 'to_approve'})

            action_id = self.env.ref('equip3_accounting_budget.action_account_purchase_change_request')
            template_id = self.env.ref('equip3_accounting_budget.email_template_application_for_purchase_budget_change_request_approval')
            # wa_template_id = self.env.ref('equip3_accounting_budget.wa_template_request_for_approval_purchase_budget_change_request')

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=purchase.change.request'
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
                    if record.is_allowed_to_wa_notification:
                        record._send_wa_request_for_approval_purchase_budget_change_req(approver, phone_num, currency, url, self.env.user.name)
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
                    'new_amount': new_amount,
                    "create_date": record.date, 
                    "currency": currency,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                if record.is_allowed_to_wa_notification:
                    record._send_wa_request_for_approval_purchase_budget_change_req(approver, phone_num, currency, url, self.env.user.name)
                # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)

    def action_for_approved(self):
        for record in self:
            record.write({'state': 'approved'})
            # for line in record.pur_change_req_ids:
            #     line._change_parent_planned_amount()

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Budget Change Request',
            'res_model': 'purchase.change.request.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    # @api.onchange('budget_std_id')
    # def _onchange_budget_std_id(self):
    #     budget_line_list = [(5, 0, 0)]
    #     for req in self:
    #         for line in req.budget_std_id.crossovered_budget_line:
    #             budget_line_list.append((0, 0, {'budgetary_position_id': line.general_budget_id.id,
    #                                             'planned_amount': line.planned_amount,
    #                                             }))
    #         req.budget_line = budget_line_list

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
        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.change.request.seq')
        return super(PurchaseChangeRequest, self).create(vals)
    
    @api.onchange('budget_std_id')
    def _onchange_budget_std_id(self):
        budget_line_list = [(5, 0, 0)]
        for req in self:
            req.write({
                'is_parent_budget': req.budget_std_id.is_parent_budget,
                'parent_budget_id': req.budget_std_id.parent_budget_id.id,
                'account_tag_ids': req.budget_std_id.account_tag_ids.ids,
                'date_from': req.budget_std_id.date_from,
                'date_to': req.budget_std_id.date_to,
            })
            for line in req.budget_std_id.purchase_budget_line:
                budget_line_list.append((0, 0, {
                                        'group_product_id': line.group_product_id.id,
                                        'product_budget': line.product_budget.id,
                                        'product_id': line.product_id.id,
                                        'account_tag_ids': line.account_tag_ids.ids,
                                        'date_from': line.date_from,
                                        'date_to': line.date_to,
                                        'planned_amount': line.planned_amount,
                                        'remaining_amount': line.remaining_amount,
                                        'new_amount': line.planned_amount,
                                                }))
            req.pur_change_req_ids = budget_line_list

    def write(self, vals):
        for req in self:
            if vals.get('state') in ['to_approve','confirm']:
                for line in req.pur_change_req_ids:
                    domain = [
                        ('product_budget', '=', line.product_budget.id),
                        ('group_product_id', '=', line.group_product_id.id),
                        ('product_id', '=', line.product_id.id),
                        ('purchase_budget_id', '=', req.budget_std_id.id),
                    ]
                    if not req.is_parent_budget:
                        domain += [('account_tag_ids','in',line.account_tag_ids.ids)]
                    budget_purchase_lines = self.env['budget.purchase.lines'].search(domain)
                    for budget_line in budget_purchase_lines:
                        if (budget_line.avail_amount + (line.new_amount - line.planned_amount)) < 0:
                            raise ValidationError("Budget has been reserved. New planned amount cannot be less than reserved amount!")

                    parent_purchase_budget_line = self.env['budget.purchase.lines'].search([
                        ('purchase_budget_id','=',req.budget_std_id.parent_budget_id.id),
                        ('group_product_id','=',line.group_product_id.id),
                        ('product_id','=',line.product_id.id),
                        ('product_budget', '=', line.product_budget.id),
                        # ('account_tag_ids','in',line.account_tag_ids.ids),
                        ('date_from','<=',line.date_from),
                        ('date_to','>=',line.date_to),
                    ])
                    if parent_purchase_budget_line and (line.new_amount - line.planned_amount) > parent_purchase_budget_line.avail_amount:
                        raise ValidationError(_('You cannot allocate more than the parent budget planned amount.'))

                    if not req.budget_std_id.is_parent_budget and req.budget_std_id.parent_id:
                        crossovered_budget_lines = self.env['crossovered.budget.lines'].search(
                            [('general_budget_id', '=', line.product_budget.id),
                             ('crossovered_budget_id', '=', req.budget_std_id.parent_id.id)])
                        for budget_line in crossovered_budget_lines:
                            if line.new_amount > budget_line.planned_amount:
                                raise ValidationError(_('%s is child budget. You cannot allocate more than the budget account reference amount.' % req.budget_std_id.name))

                    if not req.budget_std_id.is_parent_budget and req.budget_std_id.parent_budget_id:
                        if (line.new_amount - line.planned_amount) > parent_purchase_budget_line.avail_amount:
                            raise ValidationError(_('%s is child budget. You cannot allocate more than the parent budget amount.' % req.budget_std_id.name))

                    if req.budget_std_id.is_parent_budget:
                        if line.new_amount < budget_purchase_lines.reserve_amount:
                            raise ValidationError(_('%s is parent budget. You cannot allocate less than the child budget amount.' % req.budget_std_id.name))

                    if not req.budget_std_id.is_parent_budget and req.budget_std_id.parent_id:
                        crossovered_budget_lines = self.env['crossovered.budget.lines'].search(
                            [('general_budget_id', '=', line.product_budget.id),
                             ('crossovered_budget_id', '=', req.budget_std_id.parent_id.id)])
                        for budget_line in crossovered_budget_lines:
                            if (line.new_amount - line.planned_amount) > budget_line.planned_amount:
                                raise ValidationError(_('%s is child budget. You cannot allocate more than the budget account reference amount.' % req.budget_std_id.name))

                    if req.budget_std_id.is_parent_budget:
                        if line.new_amount < budget_purchase_lines.reserve_amount:
                            raise ValidationError(_('%s is parent budget. You cannot allocate less than the child budget amount.' % req.budget_std_id.name))

            if vals.get('state') in ['approved','confirm']:
                req.budget_std_id.write({
                    'is_parent_budget': req.is_parent_budget,
                    'parent_budget_id': req.parent_budget_id.id,
                    'account_tag_ids': req.account_tag_ids.ids,
                    'date_from': req.date_from,
                    'date_to': req.date_to,
                })
                for line in req.pur_change_req_ids:
                    domain = [
                        ('product_budget', '=', line.product_budget.id),
                        ('group_product_id', '=', line.group_product_id.id),
                        ('product_id', '=', line.product_id.id),
                        ('purchase_budget_id', '=', req.budget_std_id.id),
                    ]
                    if not req.is_parent_budget:
                        domain += [('account_tag_ids','in',line.account_tag_ids.ids)]
                    budget_purchase_lines = self.env['budget.purchase.lines'].search(domain)
                    for budget_line in budget_purchase_lines:
                        budget_line.write({
                            'account_tag_ids': line.account_tag_ids.ids,
                            'date_from': line.date_from,
                            'date_to': line.date_to,
                            'planned_amount': line.new_amount,
                        })
                    if not budget_purchase_lines:
                        self.env['budget.purchase.lines'].create({
                            'purchase_budget_id': req.budget_std_id.id,
                            'product_budget': line.product_budget.id,
                            'group_product_id': line.group_product_id.id,
                            'product_id': line.product_id.id,
                            'account_tag_ids': line.account_tag_ids.ids,
                            'date_from': line.date_from,
                            'date_to': line.date_to,
                            'planned_amount': line.new_amount,
                        })

        result = super(PurchaseChangeRequest, self).write(vals)
        return result

    @api.onchange('account_tag_ids')
    def _onchange_account_tag_ids(self):
        for line in self.pur_change_req_ids:
            line.account_tag_ids = line.purchase_chn_req_id.account_tag_ids.ids

    @api.onchange('date_from','date_to') 
    def _onchange_budget_date(self):
        for line in self.pur_change_req_ids:
            line.date_from = line.purchase_chn_req_id.date_from
            line.date_to = line.purchase_chn_req_id.date_to

    @api.onchange('is_parent_budget') 
    def _onchange_is_parent_budget(self):
        for budget in self:
            if budget.is_parent_budget:
                budget.account_tag_ids = False
                for line in budget.pur_change_req_ids:
                    line.account_tag_ids = False
    
class PurchaseChangeRequestLine(models.Model):
    _name = "purchase.change.request.line"
    _description = 'Purchase Change Request Line'
    
    purchase_chn_req_id = fields.Many2one('purchase.change.request', string="Purchase")
    product_id = fields.Many2one('product.product', string="Product")
    planned_amount = fields.Float(string="Current Planned Amount")
    new_amount = fields.Float(string="New Planned Amount")
    group_product_id = fields.Many2one('account.product.group', string="Group of Product")
    product_id = fields.Many2one('product.product', string="Product")
    remaining_amount = fields.Float(string='Current Remaining Amount')
    product_budget = fields.Many2one('account.budget.post', 'Budgetary Position')
    product_id_domain = fields.Char(string='Product Domain', compute='_compute_product_domain')
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    account_tag_ids_domain = fields.Char(string='Analytic Group Domain', compute='_compute_account_tag_ids_domain')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)


    @api.depends('purchase_chn_req_id.account_tag_ids')
    def _compute_account_tag_ids_domain(self):
        if self.purchase_chn_req_id:
            self.account_tag_ids_domain = json.dumps([('id','in',self.purchase_chn_req_id.account_tag_ids.ids)])

    @api.depends('product_budget', 'purchase_chn_req_id.parent_id')
    def _compute_product_domain(self):
        if self.purchase_chn_req_id.parent_id:
            self.product_id_domain = json.dumps([('categ_id.property_stock_valuation_account_id', 'in', self.product_budget.account_ids.ids)])
        else:
            self.product_id_domain = json.dumps([('product_tmpl_id.group_product', '=', False)])

    # @api.model
    # def create(self, vals):
    #     res = super(PurchaseChangeRequestLine, self).create(vals)
    #     res._change_parent_planned_amount()
    #     return res
    
    # def write(self, vals):
    #     res = super(PurchaseChangeRequestLine, self).write(vals)
    #     if 'new_amount' in vals:
    #         for record in self:
    #             record._change_parent_planned_amount()
    #     return res

    # def _change_parent_planned_amount(self):
    #     for record in self:
    #         budget_line = record.purchase_chn_req_id.budget_std_id.purchase_budget_line.filtered(lambda r: r.group_product_id.id == record.group_product_id.id)
    #         if budget_line and record.new_amount != 0:
    #             budget_line.planned_amount = record.new_amount

    @api.onchange('group_product_id')
    def _onchange_product_id(self):
        self.planned_amount = 0
        self.remaining_amount = 0
        if self.group_product_id:
            budget_line = self.purchase_chn_req_id.budget_std_id.purchase_budget_line.filtered(lambda line: line.group_product_id == self.group_product_id)
            self.planned_amount = sum(budget_line.mapped('planned_amount'))
            self.remaining_amount = sum(budget_line.mapped('remaining_amount'))

    class ApprovalMatrixAccountingLines(models.Model):
        _inherit = "approval.matrix.accounting.lines"

        account_budget_req_id = fields.Many2one('purchase.change.request', string='Account Request Budget')

