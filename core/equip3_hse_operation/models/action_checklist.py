# -*- coding: utf-8 -*-

import string
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
from pytz import timezone


class ActionCHecklist(models.Model):
    _name = 'action.checklist'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Action Checklist'
    _check_company_auto = True
    _order = 'create_date DESC'
    
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string='Branch', required=False, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    name = fields.Char(string='Number', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', True)]}, index=True, default=lambda self: _('New'))
    employee_incident_id = fields.Many2one('incident.report.employee','Incident Report')
    multiple_incident_id = fields.Many2one('incident.report.multiple','Multiple Incident Report')
    investigation_report_id = fields.Many2one('investigation.report.employee','Investigation Report')
    action_propose = fields.Text('Action Propose', required=True)
    propose_by = fields.Many2one(related='investigation_report_id.responsible_person', string='Proposed By', required=True)
    reason = fields.Text('Reason')
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('to_approve', 'Action proposed'),
            ('taken', 'Action Taken'),
            ('reject', 'Action Rejected'),
        ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    state1 = fields.Selection(related='state', tracking=False)
    state2 = fields.Selection(related='state', tracking=False)

    # approval matrix
    is_hse_action_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                     compute='is_action_checklist_approval_matrix')
    approving_matrix_action_checklist_id = fields.Many2one('approval.matrix.action.checklist', string="Approval Matrix",
                                                compute='_compute_approving_customer_matrix', store=True)
    action_checklist_user_ids = fields.One2many('action.checklist.approver.user', 'action_checklist_approver_id',
                                                string='Approver')
    approvers_ids = fields.Many2many('res.users', 'action_checklist_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    employee_id = fields.Many2one('res.users', string='Users')
    last_approved = fields.Many2one('res.users', string='Users')

    @api.onchange('investigation_report_id')
    def _onchange_employee_incident_id(self):
        for record in self:
            if record.investigation_report_id:
                record.employee_incident_id = record.investigation_report_id.employee_incident_id.id

    @api.depends('employee_incident_id', 'investigation_report_id')
    def is_action_checklist_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_hse_action_approval_matrix = IrConfigParam.get_param('is_hse_action_approval_matrix')
        for record in self:
            record.is_hse_action_approval_matrix = is_hse_action_approval_matrix

    @api.depends('employee_incident_id','investigation_report_id','branch_id','company_id')
    def _compute_approving_customer_matrix(self):
        for res in self:
            res.approving_matrix_action_checklist_id = False
            if res.is_hse_action_approval_matrix:
                approving_matrix_action_checklist_id = self.env['approval.matrix.action.checklist'].search([
                                                ('company_id', '=', res.company_id.id),
                                                ('branch_id', '=', res.branch_id.id)], limit=1)
                
                if approving_matrix_action_checklist_id:
                    res.approving_matrix_action_checklist_id = approving_matrix_action_checklist_id and approving_matrix_action_checklist_id.id or False

    @api.onchange('employee_incident_id', 'investigation_report_id', 'approving_matrix_action_checklist_id')
    def onchange_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.employee_incident_id or record.investigation_report_id:
                app_list = []
                if record.is_hse_action_approval_matrix:
                    record.action_checklist_user_ids = []
                    for rec in record.approving_matrix_action_checklist_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'action_checklist_approver_id': line.id,
                                'user_ids': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                    record.approvers_ids = app_list
                    record.action_checklist_user_ids = data

    def _compute_is_approver(self):
        for record in self:
            if record.approvers_ids:
                current_user = record.env.user
                matrix_line = sorted(record.action_checklist_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(record.action_checklist_user_ids)
                if app < a:
                    for line in record.action_checklist_user_ids[app]:
                        if current_user in line.user_ids:
                            record.is_approver = True
                        else:
                            record.is_approver = False
                else:
                    record.is_approver = False
            else:
                record.is_approver = False

    def request_approval(self):
        if len(self.action_checklist_user_ids) == 0:
            raise ValidationError(
                _("There's no action checklist approval matrix created. You have to create it first."))
        
        for record in self:
            action_id = self.env.ref('equip3_hse_operation.action_view_action_checklist_menu')
            template_id = self.env.ref('equip3_hse_operation.email_template_reminder_for_action_checklist_approval')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=action.checklist'
            if record.action_checklist_user_ids and len(record.action_checklist_user_ids[0].user_ids) > 1:
                for approved_matrix_id in record.action_checklist_user_ids[0].user_ids:
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
                approver = record.action_checklist_user_ids[0].user_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : approver.partner_id.email,
                    'approver_name' : approver.name,
                    'date': date.today(),
                    'url' : url,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
            
            record.write({'employee_id': self.env.user.id,
                          'state': 'to_approve',
                          })

            for line in record.action_checklist_user_ids:
                line.write({'approver_state': 'draft'})

    def btn_approve(self):
        for record in self:
            if record.is_hse_action_approval_matrix == True:
                sequence_matrix = [data.name for data in record.action_checklist_user_ids]
                sequence_approval = [data.name for data in record.action_checklist_user_ids.filtered(
                    lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
                max_seq = max(sequence_matrix)
                min_seq = min(sequence_approval)
                approval = record.action_checklist_user_ids.filtered(
                    lambda line: self.env.user.id in line.user_ids.ids and len(
                        line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        
                action_id = self.env.ref('equip3_hse_operation.action_view_action_checklist_menu')
                template_id = self.env.ref('equip3_hse_operation.email_template_reminder_for_action_checklist_approval_temp')
                template_app = self.env.ref('equip3_hse_operation.email_template_action_checklist_approved')
                user = self.env.user
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=action.checklist'
                
                current_user = self.env.uid
                now = datetime.now(timezone(self.env.user.tz))
                dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"

                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for line in record.action_checklist_user_ids:
                            for user in line.user_ids:
                                if current_user == user.user_ids.id:
                                    line.timestamp = fields.Datetime.now()
                                    record.approved_user_ids = [(4, current_user)]
                                    var = len(line.approved_employee_ids) + 1
                                    if line.minimum_approver <= var:
                                        line.approver_state = 'approved'
                                        string_approval = []
                                        string_approval.append(line.approval_status)
                                        if line.approval_status:
                                            string_approval.append(f"{self.env.user.name}:Approved")
                                            line.approval_status = "\n".join(string_approval)
                                            string_timestammp = [line.approved_time]
                                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                            line.approved_time = "\n".join(string_timestammp)
                                        else:
                                            line.approval_status = f"{self.env.user.name}:Approved"
                                            line.approved_time = f"{self.env.user.name}:{dateformat}"
                                        line.is_approve = True
                                    else:
                                        line.approver_state = 'pending'
                                        string_approval = []
                                        string_approval.append(line.approval_status)
                                        if line.approval_status:
                                            string_approval.append(f"{self.env.user.name}:Approved")
                                            line.approval_status = "\n".join(string_approval)
                                            string_timestammp = [line.approved_time]
                                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                            line.approved_time = "\n".join(string_timestammp)
                                        else:
                                            line.approval_status = f"{self.env.user.name}:Approved"
                                            line.approved_time = f"{self.env.user.name}:{dateformat}"
                                    line.approved_employee_ids = [(4, current_user)]

                        matrix_line = sorted(record.action_checklist_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : record.employee_id.email,
                                    'date': date.today(),
                                    'url' : url,
                                }
                            template_app.sudo().with_context(ctx).send_mail(record.id, True)
                            record.button_accept()
                            
                        else:
                            record.last_approved = self.env.user.id
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            for approving_matrix_line_user in matrix_line[0].user_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : approving_matrix_line_user.partner_id.email,
                                    'approver_name' : approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter' : record.last_approved.name,
                                    'url' : url,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                            
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved!'
                    ))
                
            else:
                record.button_accept()
        
    def action_reject_approval(self):
        for record in self:
            action_id = self.env.ref('equip3_hse_operation.action_view_action_checklist_menu')
            template_rej = self.env.ref('equip3_hse_operation.email_template_action_checklist_rejected')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=action.checklist'
            for user in record.action_checklist_user_ids:
                for check_user in user.user_ids:
                    now = datetime.now(timezone(self.env.user.tz))
                    dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
                    if self.env.uid == check_user.id:
                        user.timestamp = fields.Datetime.now()
                        user.approver_state = 'reject'
                        string_approval = []
                        string_approval.append(user.approval_status)
                        if user.approval_status:
                            string_approval.append(f"{self.env.user.name}:Rejected")
                            user.approval_status = "\n".join(string_approval)
                            string_timestammp = [user.approved_time]
                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                            user.approved_time = "\n".join(string_timestammp)
                        else:
                            user.approval_status = f"{self.env.user.name}:Rejected"
                            user.approved_time = f"{self.env.user.name}:{dateformat}"
            
            record.approved_user = self.env.user.name + ' ' + 'has been Rejected!'
            ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.employee_id.email,
                    'date': date.today(),
                    'url' : url,
                }
            template_rej.sudo().with_context(ctx).send_mail(record.id, True)
            record.write({'state': 'reject'})


    def button_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'approval.matrix.action.checklist.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            }


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('action.checklist.sequence')
        return super(ActionCHecklist, self).create(vals)
    
    @api.onchange('investigation_report_id.branch_id', 'branch_id')
    def depends_investigation(self):
        for res in self:
            if res.investigation_report_id:
                res.branch_id = res.investigation_report_id.branch_id.id

    def button_accept(self):
        for res in self:
            res.state = 'taken'

    # def button_reject(self):
    #     for res in self:
    #         res.state = 'reject'
    

class ActionChecklistApproverUser(models.Model):
    _name = 'action.checklist.approver.user'

    action_checklist_approver_id = fields.Many2one('action.checklist', string="Action Checklist", ondelete="cascade")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'action_checklist_app_emp_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('reject', 'Rejected')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'check_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(related='action_checklist_approver_id.state', string='Parent Status')

    @api.depends('action_checklist_approver_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.action_checklist_approver_id.action_checklist_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.action_checklist_approver_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.action_checklist_approver_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids
