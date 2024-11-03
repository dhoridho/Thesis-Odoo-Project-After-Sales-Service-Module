from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from datetime import datetime, date
import pytz
import requests
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

headers = {'content-type': 'application/json'}

class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"

    approval_matrix = fields.Many2one('approval.matrix.accounting', string="Approval Matrix",
                                      compute='_get_approval_matrix')
    request_partner_id = fields.Many2one('res.partner', string="Requested Partner")
    is_allowed_to_approval_matrix = fields.Boolean(string="Is Allowed Approval Matrix",
                                                   compute='_get_approve_status_from_config')
    is_allowed_to_wa_notification = fields.Boolean(string="Is Allowed WA Notification", compute='_get_approve_status_from_config')
    approved_matrix_ids = fields.One2many('approval.matrix.accounting.lines', 'account_budget_id',
                                          string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.accounting.lines', string='Approval Matrix Line',
                                              compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'),
        ('validate', 'Validated'),
        ('done', 'Done')
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)

    @api.depends('company_id', 'branch_id')
    def _get_approval_matrix(self):
        self._get_approve_status_from_config()
        for record in self:
            matrix_id = False
            matrix_id = self.env['approval.matrix.accounting'].search([
                ('company_id', '=', record.company_id.id),
                ('branch_id', '=', record.branch_id.id),
                ('approval_matrix_type', '=', 'budget')
            ], limit=1)
            record.approval_matrix = matrix_id
            record._compute_approving_matrix_lines()

    @api.depends('is_allowed_to_approval_matrix')
    def _get_approve_status_from_config(self):
        for record in self:
            # record.is_allowed_to_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_budget_approval_matrix', False)
            # record.is_allowed_to_wa_notification = self.env['ir.config_parameter'].sudo().get_param('is_wa_notification_budget', False)
            record.is_allowed_to_approval_matrix = self.env['accounting.config.settings'].search([], limit=1).is_allow_budget_approval_matrix
            record.is_allowed_to_wa_notification = self.env['accounting.config.settings'].search([], limit=1).is_allow_budget_wa_notification


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

    def _send_wa_request_for_approval_budget(self, approver, phone, currency, url, submitter=False):
        wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_request_approval_budget_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var=[{'variable' : '{approver_name}', 'value' : approver.name},
                            {'variable' : '{requester_name}', 'value' : submitter},
                            {'variable' : '{url}', 'value' : url},]
                
                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone))
            else:
                raise ValidationError(_("Broadcast Template is not set in the WA Template."))
       

    def _send_wa_approval_of_budget(self, approver, phone, create_date, submitter=False):
        wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_approval_budget_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var=[{'variable' : '{approver_name}', 'value' : approver.name},
                            {'variable' : '{requester_name}', 'value' : submitter},
                            {'variable' : '{create_date}', 'value' : create_date},]
                            
                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone))
            else:
                raise ValidationError(_("Broadcast Template is not set in the WA Template."))

    def _send_wa_rejection_of_budget(self, recipient, phone, create_date, approver = False, reason = False):
        wa_template = self.env.ref('equip3_accounting_budget.wa_template_new_rejection_budget_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var=[{'variable' : '{requester_name}', 'value' : recipient},
                             {'variable' : '{approver_name}', 'value' : approver},
                             {'variable' : '{create_date}', 'value' : create_date},
                             {'variable' : '{feedback}', 'value' : reason},]
                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone))
            else:
                raise ValidationError(_("Broadcast Template is not set in the WA Template."))
    
    def action_request_for_approval(self):
        for record in self:
            record._check_duplicate_budget()
            record._check_carryover_amount()
            # if record.parent_id:
            #     record.check_parent_budget_amount(record)
            for line in record.crossovered_budget_line:
                line._line_dates_between_budget_dates()

            action_id = self.env.ref('om_account_budget.act_crossovered_budget_view')
            template_id = self.env.ref('equip3_accounting_budget.email_template_budgets_matrix_approve_request')
            # wa_template_id = self.env.ref('equip3_accounting_budget.wa_template_request_for_approval_budget')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=crossovered.budget'
            planned_amount = sum(record.crossovered_budget_line.mapped('planned_amount'))
            currency = ''
            if record.company_id.currency_id.position == 'before':
                currency = record.company_id.currency_id.symbol + str(planned_amount)
            else:
                currency = str(planned_amount) + ' ' + record.company_id.currency_id.symbol
            record.request_partner_id = self.env.user.partner_id.id
            check_state_parent = self.env['crossovered.budget'].search([('id', '=', record.parent_id.id)], limit=1)
            if check_state_parent.state in ['cancel','draft']:
                raise ValidationError(_("You can’t approve this budget because %s is %s. Please select another parent budget.") % (check_state_parent.name, check_state_parent.state))
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
                    phone_num = str(approver.partner_id.mobile)
                    if self.is_allowed_to_wa_notification:
                        record._send_wa_request_for_approval_budget(approver, phone_num, currency, url, self.env.user.name)

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
                phone_num = str(approver.partner_id.mobile)
                if self.is_allowed_to_wa_notification:
                    record._send_wa_request_for_approval_budget(approver, phone_num, currency, url, self.env.user.name)
            record.write({'state': 'to_approve'})

    def action_approve(self):
        for record in self:
            record._check_carryover_amount()
            action_id = self.env.ref('om_account_budget.act_crossovered_budget_view')
            template_id = self.env.ref('equip3_accounting_budget.email_template_budgets_matrix_approve_request')
            template_id_submitter = self.env.ref('equip3_accounting_budget.email_template_approval_of_budget_action_approve')
            # wa_template_id = self.env.ref('equip3_accounting_budget.wa_template_request_for_approval_budget')
            # wa_template_id_submitter = self.env.ref('equip3_accounting_budget.wa_template_approval_of_budget')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=crossovered.budget'
            
            if record.is_approve_button and record.approval_matrix_line_id:
                planned_amount = sum(record.crossovered_budget_line.mapped('planned_amount'))
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
                                phone_num = str(approver.partner_id.mobile)
                                if self.is_allowed_to_wa_notification:
                                    # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, currency, url, self.env.user.name)
                                    record._send_wa_approval_of_budget(approver, phone_num, self.env.user.name)
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
                                phone_num = str(approver.partner_id.mobile)
                                if self.is_allowed_to_wa_notification:
                                    record._send_wa_approval_of_budget(approver, phone_num, self.env.user.name)

            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                record.action_budget_validate()
                approver = record.approved_matrix_ids[-1].user_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.request_partner_id.email,
                    'date': date.today(),
                    'create_date': record.create_date.date(),
                    'submitter' : self.env.user.name,
                    'url' : url,
                }
                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                phone_num = str(record.request_partner_id.mobile)
                if self.is_allowed_to_wa_notification:
                    record._send_wa_approval_of_budget(approver, phone_num, record.create_date.date(), record.request_partner_id.name)

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
            'name': 'Account Budget ',
            'res_model': 'crossovered.budget.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }
class ApprovalMatrixAccountingLines(models.Model):
    _inherit = "approval.matrix.accounting.lines"

    account_budget_id = fields.Many2one('crossovered.budget', string='Account Budget')