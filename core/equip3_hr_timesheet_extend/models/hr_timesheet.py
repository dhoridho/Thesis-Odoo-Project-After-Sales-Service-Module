# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, ValidationError
import pytz
from odoo.osv import expression
from lxml import etree

class HrTimesheet(models.Model):
    _name = 'hr.timesheet'
    _description = 'HR Timesheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    @api.returns('self')
    def _get_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False

    @api.returns('self')
    def _get_job(self):
        job_id = False
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id and employee_id.job_id:
            job_id = employee_id.job_id
        return job_id
    
    @api.returns('self')
    def _get_department(self):
        department_id = False
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id and employee_id.department_id:
            department_id = employee_id.department_id
        return department_id

    employee_id = fields.Many2one('hr.employee', default=_get_employee)
    job_id = fields.Many2one('hr.job', default=_get_job, readonly=True)
    department_id = fields.Many2one('hr.department', default=_get_department, readonly=True)
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    total_durations = fields.Float('Total Durations', store=True, readonly=True, compute='_get_total_durations')
    state = fields.Selection([('draft', 'Draft'),
                            ('to_approve', 'To Approve'), 
                            ('approved', 'Approved'),
                            ('rejected', 'Rejected')], default='draft', string='Status')
    timesheet_line_ids = fields.One2many('hr.timesheet.line', 'timesheet_id')
    approvers_ids = fields.Many2many('res.users', 'emp_timesheet_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    timesheet_approval_line_ids = fields.One2many('hr.timesheet.approval.line', 'timesheet_id')
    description = fields.Text(string="Description")

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        for rec in self:
            if rec.employee_id and rec.employee_id.job_id:
                rec.job_id = rec.employee_id.job_id
            if rec.employee_id and rec.employee_id.department_id:
                rec.department_id = rec.employee_id.department_id

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_timesheet_extend.timesheet_approval_method')
            if record.employee_id:
                if record.timesheet_approval_line_ids:
                    remove = []
                    for line in record.timesheet_approval_line_ids:
                        remove.append((2, line.id))
                    record.timesheet_approval_line_ids = remove
                if setting == 'employee_hierarchy':
                    record.timesheet_approval_line_ids = self.timesheet_emp_by_hierarchy(record)
                    self.app_list_timesheet_emp_by_hierarchy()
                else:
                    self.timesheet_approval_by_matrix(record)

    @api.onchange('employee_id', 'start_date', 'end_date')
    def _onchange_period(self):
        if (not self.employee_id) or (not self.start_date) or (not self.end_date):
            return
        self.timesheet_line_ids = [(5, 0, 0)]
        employee = self.employee_id
        period_start = self.start_date
        period_end = self.end_date
        delta = period_end - period_start
        days = [period_start + timedelta(days=i) for i in range(delta.days + 1)]
        analytic_line = self.env['account.analytic.line'].search([('employee_id','=',employee.id)])

        for date in days:
            for line in analytic_line:
                if line.date == date:
                    timesheet_lines = [(0, 0, {
                                'date': line.date,
                                'employee_id': line.employee_id.id,
                                'name': line.name,
                                'project_id': line.project_id.id,
                                'task_id': line.task_id.id,
                                'unit_amount': line.unit_amount,
                                'timesheet_id': self.id,
                                'analytic_line_id': line.id,
                                'employee_domain_ids':self.employees_ids,
                            })]
                    self.timesheet_line_ids = timesheet_lines

    @api.depends('timesheet_line_ids.unit_amount')
    def _get_total_durations(self):
        for rec in self:
            total_durations = 0.0
            for line in rec.timesheet_line_ids:
                total_durations += line.unit_amount
            rec.update({
                'total_durations': total_durations,
            })

    def timesheet_emp_by_hierarchy(self, timesheet):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(timesheet, timesheet.employee_id, data, approval_ids, seq)
        return line
    
    def get_manager(self, timesheet, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_timesheet_extend.timesheet_approval_levels')
        if not setting_level:
            raise ValidationError("Level not set")
        if not employee_manager['parent_id']['user_id']:
            return approval_ids
        while data < int(setting_level):
            approval_ids.append(
                (0, 0, {'user_ids': [(4, employee_manager['parent_id']['user_id']['id'])]}))
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager(timesheet, employee_manager['parent_id'], data, approval_ids, seq)
                break
        return approval_ids

    def app_list_timesheet_emp_by_hierarchy(self):
        for timesheet in self:
            app_list = []
            for line in timesheet.timesheet_approval_line_ids:
                app_list.append(line.user_ids.id)
            timesheet.approvers_ids = app_list

    def get_manager_hierarchy(self, timesheet, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(timesheet, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def timesheet_approval_by_matrix(self, timesheet):
        app_list = []
        approval_matrix = self.env['hr.timesheet.approval.matrix'].search([('apply_to', '=', 'by_employee')])
        matrix = approval_matrix.filtered(lambda line: timesheet.employee_id.id in line.employee_ids.ids)
        if matrix:
            data_approvers = []
            for line in matrix[0].approval_matrix_ids:
                if line.approver_types == "specific_approver":
                    data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                  'user_ids': [(6, 0, line.approvers.ids)]}))
                    for approvers in line.approvers:
                        app_list.append(approvers.id)
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data = 0
                    approvers = self.get_manager_hierarchy(timesheet, timesheet.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            timesheet.approvers_ids = app_list
            timesheet.timesheet_approval_line_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.timesheet.approval.matrix'].search([('apply_to', '=', 'by_job_position')])
            matrix = approval_matrix.filtered(lambda line: timesheet.job_id.id in line.job_ids.ids)
            if matrix:
                for line in matrix[0].approval_matrix_ids:
                    if line.approver_types == "specific_approver":
                        data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                      'user_ids': [(6, 0, line.approvers.ids)]}))
                        for approvers in line.approvers:
                            app_list.append(approvers.id)
                    elif line.approver_types == "by_hierarchy":
                        manager_ids = []
                        seq = 1
                        data = 0
                        approvers = self.get_manager_hierarchy(timesheet, timesheet.employee_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                timesheet.approvers_ids = app_list
                timesheet.timesheet_approval_line_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.timesheet.approval.matrix'].search([('apply_to', '=', 'by_department')])
                matrix = approval_matrix.filtered(lambda line: timesheet.department_id.id in line.department_ids.ids)
                if matrix:
                    for line in matrix[0].approval_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                          'user_ids': [(6, 0, line.approvers.ids)]}))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(timesheet, timesheet.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    timesheet.approvers_ids = app_list
                    timesheet.timesheet_approval_line_ids = data_approvers

    @api.depends('timesheet_approval_line_ids')
    def _compute_can_approve(self):
        for timesheet in self:
            if timesheet.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_timesheet_extend.timesheet_approval_method')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_timesheet_extend.timesheet_approval_levels')
                app_level = int(setting_level)
                current_user = timesheet.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(timesheet.timesheet_approval_line_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(timesheet.timesheet_approval_line_ids)
                    if app < app_level and app < a:
                        if current_user in timesheet.timesheet_approval_line_ids[app].user_ids:
                            timesheet.is_approver = True
                        else:
                            timesheet.is_approver = False
                    else:
                        timesheet.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(timesheet.timesheet_approval_line_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(timesheet.timesheet_approval_line_ids)
                    if app < a:
                        for line in timesheet.timesheet_approval_line_ids[app]:
                            if current_user in line.user_ids:
                                timesheet.is_approver = True
                            else:
                                timesheet.is_approver = False
                    else:
                        timesheet.is_approver = False
                else:
                    timesheet.is_approver = False
            else:
                timesheet.is_approver = False
        
    def confirm(self):
        for rec in self:
            rec.state = "to_approve"
        self.approver_mail()

    def approve(self):
        self.timesheet_approval_line_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.timesheet.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_timesheet_id':self.id, 'default_state': 'approved'},
        }

    def reject(self):
        self.timesheet_approval_line_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.timesheet.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_timesheet_id':self.id, 'default_state': 'rejected'},
        }

    def get_url(self, obj):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_id = self.env.ref('equip3_hr_timesheet_extend.hr_timesheet_approve_act_window')
        url = base_url + '/web#id=' + str(obj.id) + '&action=' + str(action_id.id) + '&view_type=form&model=hr.timesheet'
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.timesheet_approval_line_ids:
                matrix_line = sorted(rec.timesheet_approval_line_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.timesheet_approval_line_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_timesheet_extend',
                            'email_template_approover_of_timesheet')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(self)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': user.email,
                        'url': url,
                        'approver_name': user.name,
                        'emp_name': self.employee_id.name,
                    })
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,force_send=True)
                break

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_timesheet = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_timesheet_extend.number_of_repetitions_timesheet'))
        timesheet_approve = self.search([('state', '=', 'to_approve')])
        for rec in timesheet_approve:
            if rec.timesheet_approval_line_ids:
                matrix_line = sorted(rec.timesheet_approval_line_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.timesheet_approval_line_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_timesheet_extend',
                            'email_template_approover_of_timesheet')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(rec)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': user.email,
                        'url': url,
                        'approver_name': user.name,
                        'emp_name': rec.employee_id.name,
                    })
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_timesheet - 1
                        query_statement = """UPDATE hr_timesheet_approval_line set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE hr_timesheet_approval_line set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

class HrTimesheetLine(models.Model):
    _name = 'hr.timesheet.line'
    _description = 'HR Timesheet Line'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    def _domain_project_id(self):
        domain = [('allow_timesheets', '=', True)]
        if not self.user_has_groups('hr_timesheet.group_timesheet_manager'):
            return expression.AND([domain,
                ['|', ('privacy_visibility', '!=', 'followers'), ('allowed_internal_user_ids', 'in', self.env.user.ids)]
            ])
        return domain
    
    @api.returns('self')
    def _default_employee_id(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False

    def _domain_task_id(self):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            return ['|', ('privacy_visibility', '!=', 'followers'), ('allowed_user_ids', 'in', self.env.user.ids)]
        return []

    timesheet_id = fields.Many2one('hr.timesheet', ondelete='cascade')
    state = fields.Selection(related='timesheet_id.state')
    employee_domain_ids = fields.Many2many('hr.employee')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today)
    task_id = fields.Many2one(
        'project.task', 'Task', compute='_compute_task_id', store=True, readonly=False, index=True,
        domain="[('company_id', '=', company_id), ('project_id.allow_timesheets', '=', True), ('project_id', '=?', project_id)]")
    project_id = fields.Many2one(
        'project.project', 'Project', compute='_compute_project_id', store=True, readonly=False,
        domain=_domain_project_id)
    name = fields.Char('Description')
    unit_amount = fields.Float('Quantity', default=0.0)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='User', default=_default_user)
    analytic_line_id = fields.Many2one('account.analytic.line')
    attachment_file = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')
    
    @api.depends('task_id', 'task_id.project_id')
    def _compute_project_id(self):
        for line in self.filtered(lambda line: not line.project_id):
            line.project_id = line.task_id.project_id

    @api.depends('project_id')
    def _compute_task_id(self):
        for line in self.filtered(lambda line: not line.project_id):
            line.task_id = False

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id != self.task_id.project_id:
            self.task_id = False
    
    @api.depends('employee_id')
    def _compute_user_id(self):
        for line in self:
            line.user_id = line.employee_id.user_id if line.employee_id else line._default_user()
    
    @api.model
    def create(self, values):
        if values.get('project_id') and not values.get('name'):
            values['name'] = '/'
        return super(HrTimesheetLine, self).create(values)
    
    @api.model
    def write(self, values):
        if 'name' in values and not values.get('name'):
            values['name'] = '/'
        return super(HrTimesheetLine, self).write(values)

class HrTimesheetApprovalLine(models.Model):
    _name = 'hr.timesheet.approval.line'

    timesheet_id = fields.Many2one('hr.timesheet', ondelete='cascade')
    sequence = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'timesheet_line_user_approve_ids', string="Approved user")
    approval_status = fields.Char('Approval Status')
    timestamp = fields.Text('Timestamp')
    feedback = fields.Text('Feedback')
    minimum_approver = fields.Integer(default=1)
    is_approve = fields.Boolean(string="Is Approve", default=False)
    #
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='draft', string="State")
    #parent status
    state = fields.Selection(string='Parent Status', related='timesheet_id.state')

    @api.depends('timesheet_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.timesheet_id.timesheet_approval_line_ids:
            sl = sl + 1
            line.sequence = sl
    
    def update_approver_state(self):
        for rec in self:
            if rec.timesheet_id.state == 'to_approve':
                if not rec.approved_employee_ids:
                    rec.approver_state = 'draft'
                elif rec.approved_employee_ids and rec.minimum_approver == len(rec.approved_employee_ids):
                    rec.approver_state = 'approved'
                else:
                    rec.approver_state = 'pending'
            if rec.timesheet_id.state == 'rejected':
                rec.approver_state = 'refuse'
            
class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(AccountAnalyticLine, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'false')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
            
        return res
    
    