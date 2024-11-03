# -*- coding: utf-8 -*-
import babel
from odoo import models, fields, api, tools, _
from datetime import datetime, timedelta, time
from odoo.exceptions import ValidationError
import pytz
import math
import requests
from lxml import etree
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

headers = {'content-type': 'application/json'}

class Equip3HrOvertimeActual(models.Model):
    _name = 'hr.overtime.actual'
    _description = 'HR Overtime Actual'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    @api.returns('self')
    def _get_employee(self):
        emp = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        con = self.env['hr.contract'].search([('state', 'in', ['open','close']), ('employee_id', '=', emp.id)], limit=1)
        return con.employee_id or False

    def _default_domain_emp(self):
        app_list = []
        for res in self.env['hr.contract'].search([('state', 'in', ['open','close'])]):
            app_list.append(res.employee_id.id)
        return [('id', '=', app_list)]

    name = fields.Char('Number', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', default=_get_employee, required=True, domain=_default_domain_emp)
    actual_based_on = fields.Selection([('overtime_request', 'Overtime Request'),
                                        ('without_overtime_request', 'Without Overtime Request'),
                                        ('attendance', 'Attendance')],
                                       default='', required=True, string='Actual Based on')
    overtime_request = fields.Many2one('hr.overtime.request', string='Overtime Request')
    period_start = fields.Date('Period Start', required=True)
    period_end = fields.Date('Period End', required=True)
    description = fields.Text('Description', required=True)
    total_actual_hours = fields.Float('Actual Hours', store=True, readonly=True, compute='_get_total_actual_hours')
    total_coefficient_hours = fields.Float('Coefficient Hours', store=True, readonly=True, compute='_get_total_coefficient_hours')
    total_overtime_amount = fields.Float('Overtime Amount', store=True, readonly=True, compute='_get_total_overtime_amount')
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company,
                                 tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'),
                              ('convert_as_leave', 'Convert as Leave'),('rejected', 'Rejected')], default='draft', string='Status')
    is_calculated = fields.Boolean('is Calculated')
    is_admin_user = fields.Boolean('Admin User', compute='get_user')
    actual_line_ids = fields.One2many('hr.overtime.actual.line', 'actual_id')
    actual_approval_line_ids = fields.One2many('hr.overtime.actual.approval.line', 'actual_id')
    actual_attendance_line_ids = fields.One2many('hr.overtime.actual.attendance.line', 'actual_id')
    is_hide_reject = fields.Boolean(default=True, compute='_get_is_hide')
    is_hide_approve = fields.Boolean(default=True, compute='_get_is_hide')
    user_approval_ids = fields.Many2many('res.users', compute="_is_hide_approve")
    overtime_wizard_state = fields.Char('OverTime Wizard State')
    applied_to = fields.Selection([('payslip', 'Payslip'), ('extra_leave', 'Extra Leave')], default='payslip', string='Applied To', required=True)
    request_type = fields.Selection([('by_employee', 'By Employee'),
                                     ('by_manager', 'By Manager')], default='', string='Request Type')
    employee_ids = fields.Many2many('hr.employee', string='Employees', domain="[('parent_id', '=', employee_id)]")
    approvers_ids = fields.Many2many('res.users', 'act_overtime_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', 'act_overtime_approved_user_rel', string='Approved by User')
    is_overtime_approval_matrix = fields.Boolean("Is Overtime Approval Matrix", compute='_compute_is_overtime_approval_matrix')
    state1 = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Submitted'),
                               ('convert_as_leave', 'Convert as Leave'),('rejected', 'Rejected')], string='Status',
                              default='draft', tracking=False, copy=False, store=True, compute='_compute_state1')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(Equip3HrOvertimeActual, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(Equip3HrOvertimeActual, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.onchange('request_type','overtime_request','employee_id')
    def _onchange_domain_overtime_request(self):
        for rec in self:
            if rec.request_type == "by_manager":
                overtime_req_obj = self.env['hr.overtime.request'].search([('request_type','=','by_manager'),('create_uid','=',self.env.user.id),('state','=','approved')])
                overtime_req_ids = []
                for ovt in overtime_req_obj:
                    overtime_req_ids.append(ovt.id)
                if rec.overtime_request:
                    if rec.overtime_request.id not in overtime_req_ids:
                        rec.overtime_request = False
                return {'domain': {'overtime_request': [('id','in',overtime_req_ids)]}}
            elif rec.request_type == "by_employee":
                overtime_req_obj = self.env['hr.overtime.request'].search([('request_type','=','by_employee'),('employee_id','=',rec.employee_id.id),('state','=','approved')])
                overtime_req_ids = []
                for ovt in overtime_req_obj:
                    overtime_req_ids.append(ovt.id)
                if rec.overtime_request:
                    if rec.overtime_request.id not in overtime_req_ids:
                        rec.overtime_request = False
                return {'domain': {'overtime_request': [('id','in',overtime_req_ids)]}}
    
    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_is_overtime_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.overtime_approval_matrix')
            rec.is_overtime_approval_matrix = setting
    
    def custom_menu(self):
        views = [(self.env.ref('equip3_hr_attendance_overtime.hr_overtime_actual_tree_view').id, 'tree'),
                        (self.env.ref('equip3_hr_attendance_overtime.hr_overtime_actual_form_view').id, 'form')]
        if  self.env.user.has_group('equip3_hr_attendance_overtime.group_overtime_self_service') and not self.env.user.has_group('equip3_hr_attendance_overtime.group_overtime_team_approver'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Actual Overtimes by Employee',
                'res_model': 'hr.overtime.actual',
                'view_mode': 'tree,form',
                'views':views,
                'domain': [('request_type','=','by_employee'),('employee_id.user_id', '=', self.env.user.id)],
                'context':{'default_request_type':'by_employee'},
                'help':"""<p class="oe_view_nocontent_create">
                    Click Create to add new Actual Overtimes.
                </p>"""
        }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Actual Overtimes by Employee',
                'res_model': 'hr.overtime.actual',
                'view_mode': 'tree,form',
                'views':views,
                'domain': [('request_type','=','by_employee')],
                'context':{'default_request_type':'by_employee'},
                'help':"""<p class="oe_view_nocontent_create">
                    Click Create to add new Actual Overtimes.
                </p>"""
        }

    def round_up(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.ceil(n * multiplier) / multiplier

    def round_down(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.floor(n * multiplier) / multiplier

    @api.model
    def create(self, vals):
        if vals.get('actual_based_on') == "overtime_request":
            if self.search([('id', '!=', vals.get('id')), ('overtime_request', '=', vals.get('overtime_request')),
                            ('state', 'not in', ['draft','rejected'])]):
                raise ValidationError(_('The Overtime Request data you selected has been submitted and approved. Create a new request or submit actual overtime without a previous overtime request'))
        sequence = self.env['ir.sequence'].next_by_code('hr.overtime.actual')
        vals.update({'name': sequence})
        return super(Equip3HrOvertimeActual, self).create(vals)

    def write(self, vals):
        res = super(Equip3HrOvertimeActual, self).write(vals)
        if not self.env.context.get('api_bypass'):
            for rec in self:
                if rec.actual_based_on == "overtime_request":
                    if self.search([('id', '!=', rec.id), ('overtime_request', '=', rec.overtime_request.id),
                                    ('state', 'not in', ['draft','rejected'])]):
                        raise ValidationError(_('The Overtime Request data you selected has been submitted and approved. Create a new request or submit actual overtime without a previous overtime request'))
        return res
    
    @api.depends('actual_approval_line_ids')
    def _is_hide_approve(self):
        for record in self:
            if record.actual_approval_line_ids:
                sequence = [data.sequence for data in record.actual_approval_line_ids.filtered(
                    lambda line: len(line.approver_confirm.ids) != line.minimum_approver)]
                if sequence:
                    minimum_sequence = min(sequence)
                    approve_user = record.actual_approval_line_ids.filtered(lambda
                                                                                 line: self.env.user.id in line.approver_id.ids and self.env.user.id not in line.approver_confirm.ids and line.sequence == minimum_sequence)
                    if approve_user:
                        record.user_approval_ids = [(6, 0, [self.env.user.id])]
                    else:
                        record.user_approval_ids = False
                else:
                    record.user_approval_ids = False
            else:
                record.user_approval_ids = False

    @api.depends('user_approval_ids')
    def _get_is_hide(self):
        for record in self:
            if not record.user_approval_ids:
                record.is_hide_approve = True
                record.is_hide_reject = True
            else:
                record.is_hide_approve = False
                record.is_hide_reject = False

    @api.depends('employee_id')
    def get_user(self):
        if self.env.uid == 2:
            self.is_admin_user = True
        else:
            self.is_admin_user = False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            ot_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.overtime_approval_matrix')
            if ot_setting:
                setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.approval_method')
                if record.request_type == 'by_employee':
                    if record.employee_id:
                        record.employee_ids = [(4, record.employee_id.id)]
                        if record.actual_approval_line_ids:
                            remove = []
                            for line in record.actual_approval_line_ids:
                                remove.append((2, line.id))
                            record.actual_approval_line_ids = remove
                        if setting == 'employee_hierarchy':
                            record.actual_approval_line_ids = self.approval_by_hierarchy(record)
                            self.app_list_overtime_emp_by_hierarchy()
                        else:
                            self.approval_by_matrix(record)
                elif record.request_type == 'by_manager':
                    if record.actual_approval_line_ids:
                        remove = []
                        for line in record.actual_approval_line_ids:
                            remove.append((2, line.id))
                        record.actual_approval_line_ids = remove
                    if setting == 'employee_hierarchy':
                        record.actual_approval_line_ids = self.approval_by_hierarchy(record)
                        self.app_list_overtime_emp_by_hierarchy()
                    else:
                        self.approval_by_matrix(record)

    def app_list_overtime_emp_by_hierarchy(self):
        for overtime in self:
            app_list = []
            for line in overtime.actual_approval_line_ids:
                app_list.append(line.approver_id.id)
            overtime.approvers_ids = app_list

    def approval_by_matrix(self, record):
        app_list = []
        approval_matrix = self.env['hr.overtime.approval.matrix'].search([('apply_to', '=', 'by_employee')])
        matrix = approval_matrix.filtered(lambda line: record.employee_id.id in line.employee_ids.ids)

        if matrix:
            data_approvers = []
            for line in matrix[0].approval_matrix_ids:
                if line.approver_types == "specific_approver":
                    data_approvers.append((0, 0, {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                  'approver_id': [(6, 0, line.approvers.ids)]}))
                    for approvers in line.approvers:
                        app_list.append(approvers.id)
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data = 0
                    approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                        app_list.append(approver)
            record.approvers_ids = app_list
            record.actual_approval_line_ids = data_approvers
        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.overtime.approval.matrix'].search(
                [('apply_to', '=', 'by_job_position')])
            matrix = approval_matrix.filtered(lambda line: record.employee_id.job_id.id in line.job_ids.ids)
            if matrix:
                for line in matrix[0].approval_matrix_ids:
                    if line.approver_types == "specific_approver":
                        data_approvers.append((0, 0, {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                      'approver_id': [(6, 0, line.approvers.ids)]}))
                        for approvers in line.approvers:
                            app_list.append(approvers.id)
                    elif line.approver_types == "by_hierarchy":
                        manager_ids = []
                        seq = 1
                        data = 0
                        approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                            app_list.append(approver)
                record.approvers_ids = app_list
                record.actual_approval_line_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.overtime.approval.matrix'].search(
                    [('apply_to', '=', 'by_department')])
                matrix = approval_matrix.filtered(lambda line: record.employee_id.department_id.id in line.deparment_ids.ids)
                if matrix:
                    for line in matrix[0].approval_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0, 0,
                                                   {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                    'approver_id': [(6, 0, line.approvers.ids)]}))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                                app_list.append(approver)
                    record.approvers_ids = app_list
                    record.actual_approval_line_ids = data_approvers

    def approval_by_hierarchy(self,record):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(record,record.employee_id,data,approval_ids,seq)
        return line

    def get_manager(self, record, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.approval_levels')
        if not setting_level:
            raise ValidationError("level not set")
        if not employee_manager['parent_id']['user_id']:
            return approval_ids
        while data < int(setting_level):
            approval_ids.append(
                (0, 0, {'sequence': seq, 'approver_id': [(4, employee_manager['parent_id']['user_id']['id'])]}))
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager(record, employee_manager['parent_id'], data, approval_ids, seq)
                break

        return approval_ids

    def get_manager_hierarchy(self, record, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(record, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    @api.onchange('actual_based_on')
    def _onchange_actual_based_on(self):
        if self.actual_based_on:
            self.employee_ids = False
            self.overtime_request = False
            self.period_start = False
            self.period_end = False
            self.description = False
            remove = []
            for line in self.actual_line_ids:
                remove.append((2, line.id))
            self.actual_line_ids = remove

            att_remove = []
            for line in self.actual_attendance_line_ids:
                att_remove.append((2, line.id))
            self.actual_attendance_line_ids = att_remove

    @api.onchange('overtime_request')
    def _onchange_overtime_request(self):
        request = self.env['hr.overtime.request'].search([('id', '=', self.overtime_request.id)], limit=1)
        self.period_start = request.period_start
        self.period_end = request.period_end

        if self.period_start and self.period_end:
            user_tz = self.employee_id.tz or 'UTC'
            local = pytz.timezone(user_tz)
            date_min = datetime.combine(fields.Date.from_string(self.period_start), time.min)
            date_max = datetime.combine(fields.Date.from_string(self.period_end), time.max)
            date_start = local.localize(date_min).astimezone(pytz.UTC).replace(tzinfo=None)
            date_end = local.localize(date_max).astimezone(pytz.UTC).replace(tzinfo=None)

            attendances = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                            ('check_in', '>=', date_start),
                                                            ('check_in', '<=', date_end)], order='check_in')
            if attendances:
                attendance_line = []
                for att in attendances:
                    input_data = {
                        'actual_id': self.id,
                        'attendance_id': att.id,
                        'employee_id': att.employee_id.id,
                        'check_in': att.check_in,
                        'check_out': att.check_out,
                        'worked_hours': att.worked_hours,
                        'attendance_status': att.attendance_status
                    }
                    attendance_line += [input_data]

                attendance_lines = self.actual_attendance_line_ids.browse([])
                for r in attendance_line:
                    attendance_lines += attendance_lines.new(r)
                self.actual_attendance_line_ids = attendance_lines
            else:
                att_remove = []
                for line in self.actual_attendance_line_ids:
                    att_remove.append((2, line.id))
                self.actual_attendance_line_ids = att_remove

            request_line = self.env['hr.overtime.request.line'].search(
                [('request_id', '=', self.overtime_request.id)], order='date')

            if request_line:
                actual_line = []
                for rec in request_line:
                    input_data = {
                        'employee_id': rec.employee_id.id,
                        'overtime_reason': rec.overtime_reason,
                        'date': rec.date,
                        'start_time': rec.start_time,
                        'end_time': rec.end_time,
                        'hours': rec.number_of_hours,
                        'actual_start_time': rec.start_time,
                        'actual_end_time': rec.end_time,
                        'actual_id': self.id,
                    }
                    actual_line += [input_data]

                actual_lines = self.actual_line_ids.browse([])
                for r in actual_line:
                    actual_lines += actual_lines.new(r)
                self.actual_line_ids = actual_lines
            else:
                req_remove = []
                for line in self.actual_line_ids:
                    req_remove.append((2, line.id))
                self.actual_line_ids = req_remove

    @api.onchange('request_type', 'employee_id', 'period_start', 'period_end', 'actual_based_on', 'employee_ids')
    def _onchange_period(self):
        if self.request_type == 'by_employee':
            if (not self.employee_id) or (not self.period_start) or (not self.period_end) or (not self.actual_based_on) or (not self.request_type):
                return
        elif self.request_type == 'by_manager':
            if (not self.employee_ids) or (not self.period_start) or (not self.period_end) or (not self.request_type):
                return

        period_start = self.period_start
        period_end = self.period_end
        delta = period_end - period_start
        days = [period_start + timedelta(days=i) for i in range(delta.days + 1)]

        ttyme = datetime.combine(fields.Date.from_string(period_start), time.min)
        ttyme_end = datetime.combine(fields.Date.from_string(period_end), time.min)
        locale = self.env.context.get('lang') or 'en_US'
        self.description = _('Actual Overtime for period: %s to %s') % (
            tools.ustr(babel.dates.format_date(date=ttyme, format='dd MMM YYYY', locale=locale)),
            tools.ustr(babel.dates.format_date(date=ttyme_end, format='dd MMM YYYY', locale=locale)))

        user_tz = self.employee_id.tz or 'UTC'
        local = pytz.timezone(user_tz)
        date_min = datetime.combine(fields.Date.from_string(period_start), time.min)
        date_max = datetime.combine(fields.Date.from_string(period_end), time.max)
        date_start = local.localize(date_min).astimezone(pytz.UTC).replace(tzinfo=None)
        date_end = local.localize(date_max).astimezone(pytz.UTC).replace(tzinfo=None)

        attendance_line = []
        if self.request_type == 'by_employee':
            attendances = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                            ('check_in', '>=', date_start),
                                                            ('check_in', '<=', date_end)], order='check_in')
            if attendances:
                for att in attendances:
                    input_data = {
                        'actual_id': self.id,
                        'attendance_id': att.id,
                        'employee_id': att.employee_id.id,
                        'check_in': att.check_in,
                        'check_out': att.check_out,
                        'worked_hours': att.worked_hours,
                        'attendance_status': att.attendance_status
                    }
                    attendance_line += [input_data]

        elif self.request_type == 'by_manager':
            for emp in self.employee_ids.ids:
                attendances = self.env['hr.attendance'].search([('employee_id', '=', emp),
                                                            ('check_in', '>=', date_start),
                                                            ('check_in', '<=', date_end)], order='check_in')
                if attendances:
                    for att in attendances:
                        input_data = {
                            'actual_id': self.id,
                            'attendance_id': att.id,
                            'employee_id': att.employee_id.id,
                            'check_in': att.check_in,
                            'check_out': att.check_out,
                            'worked_hours': att.worked_hours,
                            'attendance_status': att.attendance_status
                        }
                        attendance_line += [input_data]

        attendance_lines = self.actual_attendance_line_ids.browse([])
        for r in attendance_line:
            attendance_lines += attendance_lines.new(r)
        self.actual_attendance_line_ids = attendance_lines

        if self.actual_based_on == 'without_overtime_request':
            actual_line = []
            for date in days:
                dates_min = datetime.combine(fields.Date.from_string(date), time.min)
                dates_max = datetime.combine(fields.Date.from_string(date), time.max)
                dates_start = local.localize(dates_min).astimezone(pytz.UTC).replace(tzinfo=None)
                dates_end = local.localize(dates_max).astimezone(pytz.UTC).replace(tzinfo=None)
                if self.request_type == 'by_employee':
                    att_obj = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                                ('check_in', '>=', dates_start),
                                                                ('check_in', '<=', dates_end)],
                                                            limit=1, order='check_in')
                    start_times = 0.0
                    end_times = 0.0
                    if att_obj:
                        check_ins = pytz.UTC.localize(att_obj.check_in).astimezone(local)
                        if date == check_ins.date():
                            start_times = att_obj.hour_to
                        if att_obj.check_out:
                            check_outs = pytz.UTC.localize(att_obj.check_out).astimezone(local)
                            checkout_times = check_outs.time()
                            if date == check_ins.date():
                                end_times = checkout_times.hour + checkout_times.minute / 60

                    input_data = {
                        'employee_id': self.employee_id.id,
                        'date': date,
                        'actual_start_time': start_times,
                        'actual_end_time': end_times,
                        'actual_id': self.id,
                    }
                    actual_line += [input_data]
                elif self.request_type == 'by_manager':
                    for emp in self.employee_ids.ids:
                        att_obj = self.env['hr.attendance'].search([('employee_id', '=', emp),
                                                                ('check_in', '>=', dates_start),
                                                                ('check_in', '<=', dates_end)],
                                                            limit=1, order='check_in')
                        start_times = 0.0
                        end_times = 0.0
                        if att_obj:
                            check_ins = pytz.UTC.localize(att_obj.check_in).astimezone(local)
                            if date == check_ins.date():
                                start_times = att_obj.hour_to
                            if att_obj.check_out:
                                check_outs = pytz.UTC.localize(att_obj.check_out).astimezone(local)
                                checkout_times = check_outs.time()
                                if date == check_ins.date():
                                    end_times = checkout_times.hour + checkout_times.minute / 60

                        input_data = {
                            'employee_id': emp,
                            'date': date,
                            'actual_start_time': start_times,
                            'actual_end_time': end_times,
                            'actual_id': self.id,
                        }
                        actual_line += [input_data]

            actual_lines = self.actual_line_ids.browse([])
            for r in actual_line:
                actual_lines += actual_lines.new(r)
            self.actual_line_ids = actual_lines
        elif self.actual_based_on == 'overtime_request':
            if self.request_type == 'by_employee':
                request_line = self.env['hr.overtime.request.line'].search(
                    [('employee_id', '=', self.employee_id.id),('date','in',days),('state','=','approved')], order='date')
                if request_line:
                    actual_line = []
                    for rec in request_line:
                        input_data = {
                            'employee_id': rec.employee_id.id,
                            'overtime_reason': rec.overtime_reason,
                            'date': rec.date,
                            'start_time': rec.start_time,
                            'end_time': rec.end_time,
                            'hours': rec.number_of_hours,
                            'actual_start_time': rec.start_time,
                            'actual_end_time': rec.end_time,
                            'actual_id': self.id,
                        }
                        actual_line += [input_data]

                    actual_lines = self.actual_line_ids.browse([])
                    for r in actual_line:
                        actual_lines += actual_lines.new(r)
                    self.actual_line_ids = actual_lines
                else:
                    req_remove = []
                    for line in self.actual_line_ids:
                        req_remove.append((2, line.id))
                    self.actual_line_ids = req_remove
            elif self.request_type == 'by_manager':
                    actual_line = []
                    request_line = self.env['hr.overtime.request.line'].search(
                        [('employee_id', 'in', self.employee_ids.ids),('date','in',days),('state','=','approved')], order='date')
                    if request_line:
                        for rec in request_line:
                            input_data = {
                                'employee_id': rec.employee_id.id,
                                'overtime_reason': rec.overtime_reason,
                                'date': rec.date,
                                'start_time': rec.start_time,
                                'end_time': rec.end_time,
                                'hours': rec.number_of_hours,
                                'actual_start_time': rec.start_time,
                                'actual_end_time': rec.end_time,
                                'actual_id': self.id,
                            }
                            actual_line += [input_data]

                        actual_lines = self.actual_line_ids.browse([])
                        for r in actual_line:
                            actual_lines += actual_lines.new(r)
                        self.actual_line_ids = actual_lines
                    else:
                        req_remove = []
                        for line in self.actual_line_ids:
                            req_remove.append((2, line.id))
                        self.actual_line_ids = req_remove
        elif self.actual_based_on == 'attendance':
            actual_line = []
            for date in days:
                if self.request_type == 'by_employee':
                    att_obj = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                                ('start_working_date', '=', date)],
                                                                limit=1, order='check_in')
                    start_times = 0.0
                    end_times = 0.0
                    if att_obj:
                        if not att_obj.calendar_id:
                            if att_obj.check_in and att_obj.check_out:
                                check_ins = pytz.UTC.localize(att_obj.check_in).astimezone(local)
                                checkin_times = check_ins.time()
                                start_times = checkin_times.hour + checkin_times.minute / 60
                                check_outs = pytz.UTC.localize(att_obj.check_out).astimezone(local)
                                checkout_times = check_outs.time()
                                end_times = checkout_times.hour + checkout_times.minute / 60

                                input_data = {
                                    'employee_id': self.employee_id.id,
                                    'date': date,
                                    'actual_start_time': start_times,
                                    'actual_end_time': end_times,
                                    'actual_id': self.id,
                                }
                                actual_line += [input_data]
                        elif att_obj.calendar_id:
                            if att_obj.check_in and att_obj.check_out:
                                check_ins = pytz.UTC.localize(att_obj.check_in).astimezone(local)
                                checkin_times = check_ins.time()
                                start_times = checkin_times.hour + checkin_times.minute / 60
                                work_hour_from = att_obj.hour_from
                                work_hour_to = att_obj.hour_to
                                check_outs = pytz.UTC.localize(att_obj.check_out).astimezone(local)
                                checkout_times = check_outs.time()
                                end_times = checkout_times.hour + checkout_times.minute / 60
                                
                                if start_times < work_hour_from:
                                    input_data = {
                                        'employee_id': self.employee_id.id,
                                        'date': date,
                                        'actual_start_time': start_times,
                                        'actual_end_time': work_hour_from,
                                        'actual_id': self.id,
                                    }
                                    actual_line += [input_data]
                                if end_times > work_hour_to:
                                    input_data = {
                                        'employee_id': self.employee_id.id,
                                        'date': date,
                                        'actual_start_time': work_hour_to,
                                        'actual_end_time': end_times,
                                        'actual_id': self.id,
                                    }
                                    actual_line += [input_data]
                elif self.request_type == 'by_manager':
                    for emp in self.employee_ids.ids:
                        att_obj = self.env['hr.attendance'].search([('employee_id', '=', emp),
                                                                    ('start_working_date', '=', date)],
                                                                    limit=1, order='check_in')
                        start_times = 0.0
                        end_times = 0.0
                        if att_obj:
                            if not att_obj.calendar_id:
                                if att_obj.check_in and att_obj.check_out:
                                    check_ins = pytz.UTC.localize(att_obj.check_in).astimezone(local)
                                    checkin_times = check_ins.time()
                                    start_times = checkin_times.hour + checkin_times.minute / 60
                                    check_outs = pytz.UTC.localize(att_obj.check_out).astimezone(local)
                                    checkout_times = check_outs.time()
                                    end_times = checkout_times.hour + checkout_times.minute / 60

                                    input_data = {
                                        'employee_id': emp,
                                        'date': date,
                                        'actual_start_time': start_times,
                                        'actual_end_time': end_times,
                                        'actual_id': self.id,
                                    }
                                    actual_line += [input_data]
                            elif att_obj.calendar_id:
                                if att_obj.check_in and att_obj.check_out:
                                    check_ins = pytz.UTC.localize(att_obj.check_in).astimezone(local)
                                    checkin_times = check_ins.time()
                                    start_times = checkin_times.hour + checkin_times.minute / 60
                                    work_hour_from = att_obj.hour_from
                                    work_hour_to = att_obj.hour_to
                                    check_outs = pytz.UTC.localize(att_obj.check_out).astimezone(local)
                                    checkout_times = check_outs.time()
                                    end_times = checkout_times.hour + checkout_times.minute / 60
                                    
                                    if start_times < work_hour_from:
                                        input_data = {
                                            'employee_id': emp,
                                            'date': date,
                                            'actual_start_time': start_times,
                                            'actual_end_time': work_hour_from,
                                            'actual_id': self.id,
                                        }
                                        actual_line += [input_data]
                                    if end_times > work_hour_to:
                                        input_data = {
                                            'employee_id': emp,
                                            'date': date,
                                            'actual_start_time': work_hour_to,
                                            'actual_end_time': end_times,
                                            'actual_id': self.id,
                                        }
                                        actual_line += [input_data]

            actual_lines = self.actual_line_ids.browse([])
            for r in actual_line:
                actual_lines += actual_lines.new(r)
            self.actual_line_ids = actual_lines

    @api.depends('actual_line_ids.actual_hours')
    def _get_total_actual_hours(self):
        for rec in self:
            total_actual_hours = 0.0
            for line in rec.actual_line_ids:
                total_actual_hours += line.actual_hours
            rec.update({
                'total_actual_hours': total_actual_hours,
            })

    @api.depends('actual_line_ids.coefficient_hours')
    def _get_total_coefficient_hours(self):
        for rec in self:
            total_coefficient_hours = 0.0
            for line in rec.actual_line_ids:
                total_coefficient_hours += line.coefficient_hours
            rec.update({
                'total_coefficient_hours': total_coefficient_hours,
            })

    @api.depends('actual_line_ids.amount')
    def _get_total_overtime_amount(self):
        for rec in self:
            total_overtime_amount = 0.0
            for line in rec.actual_line_ids:
                total_overtime_amount += line.amount
            rec.update({
                'total_overtime_amount': total_overtime_amount,
            })

    def confirm(self):
        ot_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.overtime_approval_matrix')
        for rec in self:
            if rec.actual_based_on == "without_overtime_request":
                period_start = rec.period_start
                period_end = rec.period_end
                delta = period_end - period_start
                days = [period_start + timedelta(days=i) for i in range(delta.days + 1)]
                start_of_week_data = []
                for date in days:
                    start_of_week_period = date - timedelta(days=date.weekday())
                    if start_of_week_period not in start_of_week_data:
                        start_of_week_data.append(start_of_week_period)

                ## for day limitation
                for actual_line in rec.actual_line_ids:
                    working_time = actual_line.employee_id.resource_calendar_id
                    wt_overtime_rule = working_time.overtime_rules_id
                    if wt_overtime_rule.is_use_ovt_limit:
                        ovt_limit_day_mins = wt_overtime_rule.ovt_limit_day * 60
                        ovt_limit_day_hour, ovt_limit_day_min = divmod(ovt_limit_day_mins, 60)
                        actual_line_day = self.env['hr.overtime.actual.line'].search(
                                [('employee_id', '=', actual_line.employee_id.id),('date','=',actual_line.date),('state','in',['approved'])],limit=1)
                        if actual_line_day:
                            total_hours = actual_line.actual_hours + actual_line_day.actual_hours
                            remaining_hours = wt_overtime_rule.ovt_limit_day - actual_line_day.actual_hours
                        else:
                            total_hours = actual_line.actual_hours
                            remaining_hours = wt_overtime_rule.ovt_limit_day
                        remaining_hours_mins = remaining_hours * 60
                        remaining_hours_mins_hour, remaining_hours_mins_min = divmod(remaining_hours_mins, 60)
                        if total_hours > wt_overtime_rule.ovt_limit_day:
                            raise ValidationError(_('You can only apply for %s hours %s minutes of overtime per Day. The remaining Limit for your submission on this date %s for %s is %s hour %s minute.') % (int(ovt_limit_day_hour),int(ovt_limit_day_min),actual_line.date,actual_line.employee_id.name,int(remaining_hours_mins_hour),int(remaining_hours_mins_min)))
                    else:
                        actual_other_line = rec.actual_line_ids.filtered(lambda r: r.id != actual_line.id and r.employee_id == actual_line.employee_id and r.date == actual_line.date)
                        for actual_other in actual_other_line:
                            if actual_line.actual_end_time > actual_other.actual_start_time > actual_line.actual_start_time or actual_line.actual_end_time > actual_other.actual_end_time > actual_line.actual_start_time:
                                raise ValidationError("One of your overtime request lines collides with another line. Please enter a time that does not collide with each other")
                        actual_line_approve = self.env['hr.overtime.actual.line'].search(
                                [('employee_id', '=', actual_line.employee_id.id),('date','=',actual_line.date),('state','in',['to_approve','approved'])])
                        for linex in actual_line_approve:
                            if actual_line.actual_end_time >= linex.actual_start_time >= actual_line.actual_start_time or actual_line.actual_end_time >= linex.actual_end_time >= actual_line.actual_start_time:
                                raise ValidationError("This Actual Overtime Request you are trying to submit conflicted with your other Actual Overtime Requests. Please double-check your Actual Overtime Request and ensure that the hours you submit aren't in conflict with previous requests")
                
                ## for week limitation
                if rec.request_type == "by_employee":
                    working_time = rec.employee_id.resource_calendar_id
                    wt_overtime_rule = working_time.overtime_rules_id
                    if wt_overtime_rule.is_use_ovt_limit:
                        for week in start_of_week_data:
                            end_of_week = week + timedelta(days=6)
                            sum_req_hours = 0
                            for line in rec.actual_line_ids:
                                if line.date >= week and line.date <= end_of_week:
                                    sum_req_hours += line.actual_hours
                            actual_line_week = self.env['hr.overtime.actual.line'].search(
                                    [('employee_id', '=', rec.employee_id.id),('date','>=',week),('date','<=',end_of_week),('state','in',['to_approve','approved'])])
                            if actual_line_week:
                                sum_actual_hours = sum(actual_line_week.mapped("actual_hours"))
                                total_hours = sum_req_hours + sum_actual_hours
                                remaining_hours = wt_overtime_rule.ovt_limit_week - sum_actual_hours
                            else:
                                total_hours = sum_req_hours
                                remaining_hours = wt_overtime_rule.ovt_limit_week
                            if total_hours > wt_overtime_rule.ovt_limit_week:
                                ovt_limit_week_mins = wt_overtime_rule.ovt_limit_week * 60
                                ovt_limit_week_hour, ovt_limit_week_min = divmod(ovt_limit_week_mins, 60)
                                remaining_hours_mins = remaining_hours * 60
                                remaining_hours_mins_hour, remaining_hours_mins_min = divmod(remaining_hours_mins, 60)
                                raise ValidationError(_('You can only apply for %s hours %s minutes of overtime per Week. The remaining Limit for your submission on period date from %s to %s is %s hour %s minute.') % (int(ovt_limit_week_hour),int(ovt_limit_week_min),week,end_of_week,int(remaining_hours_mins_hour),int(remaining_hours_mins_min)))
                elif rec.request_type == "by_manager":
                    for emp in rec.employee_ids:
                        working_time = emp.resource_calendar_id
                        wt_overtime_rule = working_time.overtime_rules_id
                        if wt_overtime_rule.is_use_ovt_limit:
                            actual_line = rec.actual_line_ids.filtered(lambda r: r.employee_id == emp)
                            for week in start_of_week_data:
                                end_of_week = week + timedelta(days=6)
                                sum_req_hours = 0
                                for line in actual_line:
                                    if line.date >= week and line.date <= end_of_week:
                                        sum_req_hours += line.actual_hours
                                actual_line_week = self.env['hr.overtime.actual.line'].search(
                                        [('employee_id', '=', emp.id),('date','>=',week),('date','<=',end_of_week),('state','in',['to_approve','approved'])])
                                if actual_line_week:
                                    sum_actual_hours = sum(actual_line_week.mapped("actual_hours"))
                                    total_hours = sum_req_hours + sum_actual_hours
                                    remaining_hours = wt_overtime_rule.ovt_limit_week - sum_actual_hours
                                else:
                                    total_hours = sum_req_hours
                                    remaining_hours = wt_overtime_rule.ovt_limit_week
                                if total_hours > wt_overtime_rule.ovt_limit_week:
                                    ovt_limit_week_mins = wt_overtime_rule.ovt_limit_week * 60
                                    ovt_limit_week_hour, ovt_limit_week_min = divmod(ovt_limit_week_mins, 60)
                                    remaining_hours_mins = remaining_hours * 60
                                    remaining_hours_mins_hour, remaining_hours_mins_min = divmod(remaining_hours_mins, 60)
                                    raise ValidationError(_('Employee %s can only apply for %s hours %s minutes of overtime per Week. The remaining Limit for your submission on period date from %s to %s is %s hour %s minute.') % (line.employee_id.name,int(ovt_limit_week_hour),int(ovt_limit_week_min),week,end_of_week,int(remaining_hours_mins_hour),int(remaining_hours_mins_min)))
                                
            if rec.applied_to == "payslip" and rec.is_calculated  == False:
                raise ValidationError(_("""Please calculate overtime first!"""))
            else:
                if ot_setting:
                    if not rec.actual_approval_line_ids:
                        rec.state = "approved"
                        # rec.message_post(body=_('Status: Draft -> Approved'))
                    else:
                        rec.state = "to_approve"
                        # rec.message_post(body=_('Status: Draft -> To Approve'))

                    for line in rec.actual_line_ids:
                        line.state = rec.state
            if ot_setting:
                rec.approver_mail()
                rec.approver_wa_template()
                for line in rec.actual_approval_line_ids:
                    line.write({'approver_state': 'draft'})
            else:
                rec.write({'state': 'approved'})
                for line in rec.actual_line_ids:
                    line.write({'state': 'approved'})

    def approve(self):
        self.update({
            'overtime_wizard_state': 'approved',
        })
        self.actual_approval_line_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.overtime.actual.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_overtime_id':self.id},
        }

    def reject(self):
        self.update({
            'overtime_wizard_state': 'rejected',
        })
        self.actual_approval_line_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.overtime.actual.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_overtime_id':self.id,
                        'default_state':self.overtime_wizard_state},
        }

    def reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.actual_approval_line_ids.unlink()
            rec.actual_approval_line_ids = False
            rec._onchange_employee_id()
            
    def convert_to_leave(self):
        self.update({
            'overtime_wizard_state': 'convert_as_leave',
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.overtime.actual.convert.leave',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Convert to Leave",
            'target': 'new',
            'context':{'default_overtime_id':self.id},
        }

    @api.constrains('actual_line_ids')
    def _check_overtime_reason(self):
        for rec in self:
            for line in rec.actual_line_ids:
                if not line.overtime_reason:
                    raise ValidationError(_("""You must filled overtime reason."""))

    @api.model
    def get_contract(self, employee, date_from, date_to):
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), ('state', 'in', ['open','close']), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids

    def calculate_overtime(self):
        for ovt in self:
            overtime_rounding = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.overtime_rounding')
            overtime_rounding_type = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.overtime_rounding_type')
            overtime_rounding_digit = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.overtime_rounding_digit')
            act_ovt_line = ovt.actual_line_ids
            for act in act_ovt_line:
                user_tz = act.employee_id.tz or 'UTC'
                local = pytz.timezone(user_tz)
                emp_work_schedule = self.env['employee.working.schedule.calendar'].search(
                    [('employee_id', '=', act.employee_id.id), ('date_start', '=', act.date)], limit=1)
                if emp_work_schedule:
                    working_time = emp_work_schedule.working_hours
                    if not working_time.overtime_rules_id:
                        raise ValidationError(_("Employee %s, doesn't have an overtime rules on %s") % (act.employee_id.name,act.date))
                else:
                    working_time = act.employee_id.resource_calendar_id
                week_working_day = working_time.week_working_day

                wt_overtime_rule = working_time.overtime_rules_id

                if not wt_overtime_rule:
                        raise ValidationError(_("Employee %s, doesn't have an overtime rules") % (act.employee_id.name))

                working_schedule_cal = self.env['employee.working.schedule.calendar'].search([('employee_id', '=', act.employee_id.id)])
                shortday_schedule_cal = self.env['employee.working.schedule.calendar'].search([('is_holiday', '=', True),
                                                                                            ('dayofweek', '=', 4)])

                day_dict = []
                for cal in working_schedule_cal:
                    if cal.day_type != "day_off":
                        day_dict += [cal.date_start]

                shortday_dict = []
                for shortcal in shortday_schedule_cal:
                    shortday_dict += [shortcal.date_start]

                if ovt.actual_based_on == 'attendance':
                    att_obj = self.env['hr.attendance'].search([('employee_id', '=', act.employee_id.id),
                                                                ('start_working_date', '=', act.date)],
                                                                limit=1, order='check_in')
                    start_times = act.actual_start_time
                    end_times = act.actual_end_time
                    if att_obj:
                        if att_obj.calendar_id:
                            if att_obj.check_in:
                                check_ins = pytz.UTC.localize(att_obj.check_in).astimezone(local)
                                checkin_times = check_ins.time()
                                start_times = checkin_times.hour + checkin_times.minute / 60
                                if act.actual_start_time < start_times:
                                    act.actual_start_time = start_times

                            if att_obj.check_out:
                                check_outs = pytz.UTC.localize(att_obj.check_out).astimezone(local)
                                checkout_times = check_outs.time()
                                end_times = checkout_times.hour + checkout_times.minute / 60
                                if act.actual_end_time > end_times:
                                    act.actual_end_time = end_times

                if wt_overtime_rule.use_government_rule:
                    day_name = act.date.strftime("%A")

                    contract_ids = self.get_contract(act.employee_id, act.date, act.date)
                    if not contract_ids:
                        raise ValidationError(_("Contract not found for employee %s and date %s of actual overtime line!") % (act.employee_id.name,act.date))
                    contracts = self.env['hr.contract'].browse(contract_ids)
                    slip_lines = self._get_payslip_lines(contract_ids, contracts[0].id)
                    salary_amounts = 0.0
                    for rec in slip_lines:
                        if rec['amount_select'] == 'fix':
                            amount = rec['amount_fix']
                        elif rec['amount_select'] == 'percentage':
                            amount = rec['amount'] * rec['rate'] / 100
                        else:
                            amount = rec['amount']
                        salary_amounts += amount

                    works_day = wt_overtime_rule.works_day
                    last_works_day_line = works_day.search([], order='id desc', limit=1).id
                    off_days_working = wt_overtime_rule.off_days_working
                    last_off_days_working_line = off_days_working.search([], order='id desc', limit=1).id
                    off_days_working_per_week = wt_overtime_rule.off_days_working_per_week
                    last_off_days_working_per_week_line = off_days_working_per_week.search([], order='id desc', limit=1).id
                    off_days_public_holiday = wt_overtime_rule.off_days_public_holiday
                    last_off_days_public_holiday_line = off_days_public_holiday.search([], order='id desc', limit=1).id

                    #overtime rules meal allowance
                    meal_alw_works_day = wt_overtime_rule.meal_allowance_work_days
                    meal_alw_offtime_five_day = wt_overtime_rule.meal_allowance_offtime_five_days
                    meal_alw_offtime_six_day = wt_overtime_rule.meal_allowance_offtime_six_days
                    meal_allowance_off_public_holiday = wt_overtime_rule.meal_allowance_off_public_holiday

                    total_coefficient = 0.0
                    amounts = 0.0
                    counter = 1
                    hours = act.actual_hours
                    alw_amount = 0.0

                    if act.date in shortday_dict:
                        for rec in off_days_public_holiday:
                            if rec.hour < hours:
                                while counter <= rec.hour:
                                    total_coefficient += rec.values
                                    if rec.fix_amount:
                                        amounts += rec.amount
                                    hours -= 1
                                    counter += 1
                            elif counter <= rec.hour:
                                while counter <= rec.hour and counter <= act.actual_hours:
                                    total_coefficient += rec.values
                                    if rec.fix_amount:
                                        amounts += rec.amount
                                    hours -= 1
                                    counter += 1
                                if rec.id == last_off_days_public_holiday_line:
                                    if act.actual_hours > rec.hour:
                                        total_coefficient += rec.values
                                        if rec.fix_amount:
                                            amounts += rec.amount
                        for meal in meal_allowance_off_public_holiday:
                            if act.actual_hours >= meal.minimum_hours:
                                alw_amount = meal.meal_allowance
                    elif act.date in day_dict:
                        for rec in works_day:
                            if rec.hour < hours:
                                while counter <= rec.hour:
                                    total_coefficient += rec.values
                                    if rec.fix_amount:
                                        amounts += rec.amount
                                    hours -= 1
                                    counter += 1
                            elif counter <= rec.hour:
                                while counter <= rec.hour and counter <= act.actual_hours:
                                    total_coefficient += rec.values
                                    if rec.fix_amount:
                                        amounts += rec.amount
                                    hours -= 1
                                    counter += 1
                                if rec.id == last_works_day_line:
                                    if act.actual_hours > rec.hour:
                                        total_coefficient += rec.values
                                        if rec.fix_amount:
                                            amounts += rec.amount
                        for meal in meal_alw_works_day:
                            if act.actual_hours >= meal.minimum_hours:
                                alw_amount = meal.meal_allowance
                    elif act.date not in day_dict and week_working_day == 5:
                        for rec in off_days_working:
                            if rec.hour < hours:
                                while counter <= rec.hour:
                                    total_coefficient += rec.values
                                    if rec.fix_amount:
                                        amounts += rec.amount
                                    hours -= 1
                                    counter += 1
                            elif counter <= rec.hour:
                                while counter <= rec.hour and counter <= act.actual_hours:
                                    total_coefficient += rec.values
                                    if rec.fix_amount:
                                        amounts += rec.amount
                                    hours -= 1
                                    counter += 1
                                if rec.id == last_off_days_working_line:
                                    if act.actual_hours > rec.hour:
                                        total_coefficient += rec.values
                                        if rec.fix_amount:
                                            amounts += rec.amount
                        for meal in meal_alw_offtime_five_day:
                            if act.actual_hours >= meal.minimum_hours:
                                alw_amount = meal.meal_allowance
                    elif act.date not in day_dict and week_working_day == 6:
                        for rec in off_days_working_per_week:
                            if rec.hour < hours:
                                while counter <= rec.hour:
                                    total_coefficient += rec.values
                                    if rec.fix_amount:
                                        amounts += rec.amount
                                    hours -= 1
                                    counter += 1
                            elif counter <= rec.hour:
                                while counter <= rec.hour and counter <= act.actual_hours:
                                    total_coefficient += rec.values
                                    if rec.fix_amount:
                                        amounts += rec.amount
                                    hours -= 1
                                    counter += 1
                                if rec.id == last_off_days_working_per_week_line:
                                    if act.actual_hours > rec.hour:
                                        total_coefficient += rec.values
                                        if rec.fix_amount:
                                            amounts += rec.amount
                        for meal in meal_alw_offtime_six_day:
                            if act.actual_hours >= meal.minimum_hours:
                                alw_amount = meal.meal_allowance
                    
                    multiplier_rules = []
                    if act.date in shortday_dict:
                        for rec in off_days_public_holiday:
                            multiplier_rules += [{'hour':rec.hour,'values':rec.values}]
                    elif act.date in day_dict:
                        for rec in works_day:
                            multiplier_rules += [{'hour':rec.hour,'values':rec.values}]
                    elif act.date not in day_dict and week_working_day == 5:
                        for rec in off_days_working:
                            multiplier_rules += [{'hour':rec.hour,'values':rec.values}]
                    elif act.date not in day_dict and week_working_day == 6:
                        for rec in off_days_working_per_week:
                            multiplier_rules += [{'hour':rec.hour,'values':rec.values}]
                    actual_hour_float = act.actual_hours
                    counted_hour = 1.0
                    separated_hour = []
                    while counted_hour:
                        if actual_hour_float < 1:
                            separated_hour.append(actual_hour_float)
                            break
                        separated_hour.append(1.0)
                        counted_hour += 1.0
                        if (actual_hour_float - (counted_hour-1)) <= 1:
                            separated_hour.append(actual_hour_float - (counted_hour-1))
                            break
                    index = 0 
                    total_multiplier = 0.0
                    ot_rules_index = 0
                    rule_in_use = multiplier_rules[ot_rules_index]
                    for hour in separated_hour :
                        if index == rule_in_use['hour']:
                            ot_rules_index += 1
                            rule_in_use = multiplier_rules[ot_rules_index]
                        total_multiplier += hour * rule_in_use['values']
                        index += 1
                    # I called it 'multiplier' beacuse it's "pengali" in Indonesian Bahasa before "koefisien" 
                    total_coefficient = round(total_multiplier,3)
                    total_amount = ((total_coefficient * salary_amounts) / 173) + amounts

                    total_amount_digit = len(str(int(total_amount))) - 1
                    if int(overtime_rounding_digit) >= total_amount_digit:
                        overtime_rounding_digit = total_amount_digit
                    
                    if overtime_rounding:
                        if overtime_rounding_type == 'round':
                            total_amount = round(total_amount,-abs(int(overtime_rounding_digit)))
                        if overtime_rounding_type == 'round_up':
                            total_amount = self.round_up(total_amount,-abs(int(overtime_rounding_digit)))
                        elif overtime_rounding_type == 'round_down':
                            total_amount = self.round_down(total_amount,-abs(int(overtime_rounding_digit)))
                    act.update({
                        'coefficient_hours': total_coefficient,
                        'amount': total_amount,
                        'meal_allowance': alw_amount
                    })
                else:
                    ovt_work_day = wt_overtime_rule.rules_line_ids
                    ovt_off_five_day = wt_overtime_rule.off_days_five_ids
                    ovt_off_six_day = wt_overtime_rule.off_days_six_ids
                    ovt_off_public_holiday = wt_overtime_rule.off_days_public_ids

                    meal_alw_works_day = wt_overtime_rule.meal_allowance_rules_line_ids
                    meal_alw_offtime_five_day = wt_overtime_rule.meal_allowance_off_five_ids
                    meal_alw_offtime_six_day = wt_overtime_rule.meal_allowance_off_six_ids
                    meal_allowance_off_public_holiday = wt_overtime_rule.meal_allowance_off_public_ids

                    total_amount = 0
                    alw_amount = 0

                    if act.date in shortday_dict:
                        for rec in ovt_off_public_holiday:
                            if rec.interval > 0:
                                pengali = act.actual_hours / rec.interval
                                total_amount = pengali * rec.amount
                        for meal in meal_allowance_off_public_holiday:
                            if act.actual_hours >= meal.minimum_hours:
                                alw_amount = meal.meal_allowance
                    elif act.date in day_dict:
                        for rec in ovt_work_day:
                            if rec.interval > 0:
                                pengali = act.actual_hours / rec.interval
                                total_amount = pengali * rec.amount
                        for meal in meal_alw_works_day:
                            if act.actual_hours >= meal.minimum_hours:
                                alw_amount = meal.meal_allowance
                    elif act.date not in day_dict and week_working_day == 5:
                        for rec in ovt_off_five_day:
                            if rec.interval > 0:
                                pengali = act.actual_hours / rec.interval
                                total_amount = pengali * rec.amount
                        for meal in meal_alw_offtime_five_day:
                            if act.actual_hours >= meal.minimum_hours:
                                alw_amount = meal.meal_allowance
                    elif act.date not in day_dict and week_working_day == 6:
                        for rec in ovt_off_six_day:
                            if rec.interval > 0:
                                pengali = act.actual_hours / rec.interval
                                total_amount = pengali * rec.amount
                        for meal in meal_alw_offtime_six_day:
                            if act.actual_hours >= meal.minimum_hours:
                                alw_amount = meal.meal_allowance

                    act.update({
                        'amount': total_amount,
                        'meal_allowance': alw_amount
                    })

            ovt.update({
                'is_calculated': True
            })

    @api.model
    def _get_payslip_lines(self, contract_ids, contract_id):

        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and \
                                                          localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, dict, env):
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        # we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules_dict = {}
        blacklist = []
        contract_obj = self.env['hr.contract'].browse(contract_id)

        categories = BrowsableObject(contract_obj.employee_id.id, {}, self.env)
        rules = BrowsableObject(contract_obj.employee_id.id, rules_dict, self.env)
        payslips = self.env['hr.payslip'].browse()
        inputs = self.env['hr.payslip.input'].browse()
        worked_days = self.env['hr.payslip.worked_days'].browse()

        baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days,
                         'inputs': inputs}
        # get the ids of the structures on the contracts and their parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        if len(contracts) == 1 and contract_obj.struct_id:
            structure_ids = list(set(contract_obj.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        # get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        # run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)
        sorted_rules = sorted_rules.filtered(lambda line: line.apply_to_overtime_calculation == True)

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee, contract=contract)
            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                # check if the rule can be applied
                if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                    # compute the amount of the rule
                    try:
                        amount, qty, rate = rule._compute_rule(localdict)
                    except:
                        amount = 0.0
                        qty = 1.0
                        rate = 100
                    # check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    # set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                    # create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'apply_to_overtime_calculation': rule.apply_to_overtime_calculation,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_percentage': rule.amount_percentage,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }
                else:
                    # blacklist this rule and its children
                    blacklist += [id for id, seq in rule._recursive_search_of_rules()]

        return list(result_dict.values())

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_attendance_overtime', 'hr_actual_overtime_approval_menu')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_attendance_overtime', 'hr_overtime_actual_approval_act_window')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.overtime.actualt&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.actual_approval_line_ids:
                matrix_line = sorted(rec.actual_approval_line_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.actual_approval_line_ids[len(matrix_line)]
                for user in approver.approver_id:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_attendance_overtime',
                            'email_template_approver_of_actual_approval')[1]
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
                    if self.period_start:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(self.period_start).strftime('%d/%m/%Y')})
                    if self.period_end:
                        ctx.update(
                            {'date_to': fields.Datetime.from_string(self.period_end).strftime('%d/%m/%Y')})
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.actual_approval_line_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_attendance_overtime',
                        'email_template_approved_actual_overtime')[1]
                except ValueError:
                    template_id = False
                ctx = self._context.copy()
                url = self.get_url(self)
                ctx.update({
                    'email_from': self.env.user.email,
                    'email_to': self.employee_id.user_id.email,
                    'url': url,
                    'emp_name': self.employee_id.name,
                })
                if self.period_start:
                    ctx.update(
                        {'date_from': fields.Datetime.from_string(self.period_start).strftime('%d/%m/%Y')})
                if self.period_end:
                    ctx.update(
                        {'date_to': fields.Datetime.from_string(self.period_end).strftime('%d/%m/%Y')})
                self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                          force_send=True)
            break

    def reject_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.actual_approval_line_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_attendance_overtime',
                        'email_template_rejection_of_actual_overtime_req')[1]
                except ValueError:
                    template_id = False
                ctx = self._context.copy()
                ctx.pop('default_state')
                url = self.get_url(self)
                ctx.update({
                    'email_from': self.env.user.email,
                    'email_to': self.employee_id.user_id.email,
                    'url': url,
                    'emp_name': self.employee_id.name,
                })
                if self.period_start:
                    ctx.update(
                        {'date_from': fields.Datetime.from_string(self.period_start).strftime('%d/%m/%Y')})
                if self.period_end:
                    ctx.update(
                        {'date_to': fields.Datetime.from_string(self.period_end).strftime('%d/%m/%Y')})
                self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                          force_send=True)
            break

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.send_by_wa_overtimes')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(self)
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_overtime.actual_overtime_approver_wa_template')
            wa_sender = waParam()
            if template:
                if self.actual_approval_line_ids:
                    matrix_line = sorted(self.actual_approval_line_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.actual_approval_line_ids[len(matrix_line)]
                    for user in approver.approver_id:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", self.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.name)
                        if "${start_date}" in string_test:
                            string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                                self.period_start).strftime('%d/%m/%Y'))
                        if "${end_date}" in string_test:
                            string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                                self.period_end).strftime('%d/%m/%Y'))
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${br}" in string_test:
                            string_test = string_test.replace("${br}", f"\n")
                        if "${url}" in string_test:
                            string_test = string_test.replace("${url}", url)
                        phone_num = str(user.mobile_phone)
                        if "+" in phone_num:
                            phone_num = int(phone_num.replace("+", ""))
                        
                        wa_sender.set_wa_string(string_test,template._name,template_id=template)
                        wa_sender.send_wa(phone_num)
                        
                        # param = {'body': string_test, 'phone': phone_num}
                        # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                        # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                        # try:
                        #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
                        # except ConnectionError:
                        #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.send_by_wa_overtimes')
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_overtime.actual_overtime_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.actual_approval_line_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.period_start).strftime('%d/%m/%Y'))
                    if "${end_date}" in string_test:
                        string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                            self.period_end).strftime('%d/%m/%Y'))
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)
                    if "+" in phone_num:
                        phone_num = int(phone_num.replace("+", ""))
                    if "${url}" in string_test:
                        string_test = string_test.replace("${url}", url)
                    
                    wa_sender.set_wa_string(string_test,template._name,template_id=template)
                    wa_sender.send_wa(phone_num)
                    
                    # param = {'body': string_test, 'phone': phone_num}
                    # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                    # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                    # try:
                    #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                    #                                    headers=headers, verify=True)
                    # except ConnectionError:
                    #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def rejected_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.send_by_wa_overtimes')
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_overtime.actual_overtime_rejected_wa_template')
            url = self.get_url(self)
            wa_sender = waParam()
            if template:
                if self.actual_approval_line_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.period_start).strftime('%d/%m/%Y'))
                    if "${end_date}" in string_test:
                        string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                            self.period_end).strftime('%d/%m/%Y'))
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)
                    if "+" in phone_num:
                        phone_num = int(phone_num.replace("+", ""))
                    
                    wa_sender.set_wa_string(string_test,template._name,template_id=template)
                    wa_sender.send_wa(phone_num)
                    
                    # param = {'body': string_test, 'phone': phone_num}
                    # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                    # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                    # try:
                    #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                    #                                    headers=headers, verify=True)
                    # except ConnectionError:
                    #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def get_auto_follow_up_approver_wa_template(self, rec):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.send_by_wa_overtimes')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(rec)
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_overtime.actual_overtime_approver_wa_template')
            wa_sender = waParam()
            if template:
                if rec.actual_approval_line_ids:
                    matrix_line = sorted(rec.actual_approval_line_ids.filtered(lambda r: r.is_approve == True))
                    approver = rec.actual_approval_line_ids[len(matrix_line)]
                    for user in approver.approver_id:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", rec.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", rec.name)
                        if "${start_date}" in string_test:
                            string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                                rec.period_start).strftime('%d/%m/%Y'))
                        if "${end_date}" in string_test:
                            string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                                rec.period_end).strftime('%d/%m/%Y'))
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${br}" in string_test:
                            string_test = string_test.replace("${br}", f"\n")
                        if "${url}" in string_test:
                            string_test = string_test.replace("${url}", url)
                        phone_num = str(user.mobile_phone)
                        if "+" in phone_num:
                            phone_num = int(phone_num.replace("+", ""))
                        
                        wa_sender.set_wa_string(string_test,template._name,template_id=template)
                        wa_sender.send_wa(phone_num)
                        
                        # param = {'body': string_test, 'phone': phone_num}
                        # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                        # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                        # try:
                        #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
                        # except ConnectionError:
                        #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_overtime = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_attendance_overtime.number_of_repetitions_overtime'))
        overtime_approve = self.search([('state', '=', 'to_approve')])
        for rec in overtime_approve:
            if rec.actual_approval_line_ids:
                matrix_line = sorted(rec.actual_approval_line_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.actual_approval_line_ids[len(matrix_line)]
                for user in approver.approver_id:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_attendance_overtime',
                            'email_template_approver_of_actual_approval')[1]
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
                    if rec.period_start:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(rec.period_start).strftime('%d/%m/%Y')})
                    if rec.period_end:
                        ctx.update(
                            {'date_to': fields.Datetime.from_string(rec.period_end).strftime('%d/%m/%Y')})
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_overtime - 1
                        query_statement = """UPDATE hr_overtime_actual_approval_line set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                        self.get_auto_follow_up_approver_wa_template(rec)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approver_confirm and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE hr_overtime_actual_approval_line set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
                            self.get_auto_follow_up_approver_wa_template(rec)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        overtime_approve = self.search([('state', '=', 'to_approve')])
        for rec in overtime_approve:
            if rec.actual_approval_line_ids:
                matrix_line = sorted(rec.actual_approval_line_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.actual_approval_line_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in approver.approver_confirm.ids and user.user_delegation_id.id not in approver.approver_confirm.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_attendance_overtime',
                                    'email_template_approver_of_actual_approval')[1]
                            except ValueError:
                                template_id = False
                            ctx = self._context.copy()
                            url = self.get_url(rec)
                            ctx.update({
                                'email_from': self.env.user.email,
                                'email_to': user.user_delegation_id.email,
                                'url': url,
                                'approver_name': user.user_delegation_id.name,
                                'emp_name': rec.employee_id.name,
                            })
                            if rec.period_start:
                                ctx.update(
                                    {'date_from': fields.Datetime.from_string(rec.period_start).strftime('%d/%m/%Y')})
                            if rec.period_end:
                                ctx.update(
                                    {'date_to': fields.Datetime.from_string(rec.period_end).strftime('%d/%m/%Y')})
                            approver.update({
                                'approver_id': [(4, user.user_delegation_id.id)],
                                'is_delegation_mail_sent': True,
                            })
                            rec.update({
                                'approvers_ids': [(4, user.user_delegation_id.id)],
                            })
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

class Equip3HrOvertimeActualLine(models.Model):
    _name = 'hr.overtime.actual.line'
    _order = 'create_date desc'

    @api.returns('self')
    def _get_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False

    actual_id = fields.Many2one('hr.overtime.actual', ondelete="cascade")
    employee_id = fields.Many2one('hr.employee', string='Employee', default=_get_employee, required=True)
    overtime_reason = fields.Char('Overtime Reason')
    date = fields.Date('Date')
    name_of_day = fields.Char('Name of Day', store=True, readonly=True, compute='_get_name_of_day')
    start_time = fields.Float('Start Time', readonly=True)
    end_time = fields.Float('End Time', readonly=True)
    hours = fields.Float('Hours', readonly=True)
    actual_start_time = fields.Float('Actual Start Time', required=True)
    actual_end_time = fields.Float('Actual End Time', required=True)
    break_time = fields.Float('Break Time', store=True, readonly=True, compute='_compute_break_time')
    actual_hours = fields.Float('Actual Hours', store=True, readonly=True, compute='_compute_actual_hours')
    coefficient_hours = fields.Float('Coefficient Hours')
    amount = fields.Float('Overtime Fee')
    meal_allowance = fields.Float('Meal Allowance')
    state = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'),
                              ('rejected', 'Rejected')], default='draft', string='Status')
    applied_to = fields.Selection(related='actual_id.applied_to', string='Applied To')
    
    @api.onchange('actual_start_time', 'actual_end_time')
    def _onchange_hours(self):
        self.actual_start_time = min(self.actual_start_time, 23.99)
        self.actual_start_time = max(self.actual_start_time, 0.0)
        self.actual_end_time = min(self.actual_end_time, 23.99)
        self.actual_end_time = max(self.actual_end_time, 0.0)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(Equip3HrOvertimeActualLine, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(Equip3HrOvertimeActualLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(Equip3HrOvertimeActualLine, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)  
        if self.env.user.has_group('equip3_hr_attendance_overtime.group_overtime_team_approver'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res
    
    def custom_menu(self):
        views = [
            (self.env.ref('equip3_hr_attendance_overtime.hr_overtime_actual_lines_tree_view').id, 'tree'),
            (self.env.ref('equip3_hr_attendance_overtime.hr_overtime_actual_lines_form_view').id, 'form')]
        if  self.env.user.has_group('equip3_hr_attendance_overtime.group_overtime_self_service') and not self.env.user.has_group('equip3_hr_attendance_overtime.group_overtime_team_approver'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Actual Overtimes Lines',
                'res_model': 'hr.overtime.actual.line',
                'view_mode': 'tree,form',
                'views':views,
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                'context':{},
                'help':"""<p class="oe_view_nocontent_create">
                    Click Create to add new Actual Overtimes Lines.
                </p>"""
        }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Actual Overtimes Lines',
                'res_model': 'hr.overtime.actual.line',
                'view_mode': 'tree,form',
                'views':views,
                'domain': [],
                'context':{},
                'help':"""<p class="oe_view_nocontent_create">
                    Click Create to add new Actual Overtimes Lines.
                </p>"""
        }
            
    @api.model
    def create(self, vals):
        # employee = self.env['hr.employee'].search([('id','=',vals.get('employee_id'))],limit=1)
        # if self.search([('date', '=', vals.get('date')), ('id', '!=', vals.get('id')), ('employee_id', '=', vals.get('employee_id')),
        #                 ('actual_id', '!=', vals.get('actual_id')), ('state', 'not in', ['draft','rejected'])]):
        #     raise ValidationError(_('Date %s for %s has been actualized!') % (
        #         vals.get('date'),employee.name))
        # elif self.search([('date', '=', vals.get('date')), ('id', '!=', vals.get('id')), ('employee_id', '=', vals.get('employee_id')),
        #                   ('actual_id', '=', vals.get('actual_id'))]):
        #     raise ValidationError(_('Duplicate date %s for %s !') % (
        #         vals.get('date'),employee.name))
        return super(Equip3HrOvertimeActualLine, self).create(vals)

    def write(self, vals):
        res = super(Equip3HrOvertimeActualLine, self).write(vals)
        # for rec in self:
        #     if self.search([('date', '=', rec.date), ('id', '!=', rec.id), ('actual_id', '!=', rec.actual_id.id), ('employee_id', '=', rec.employee_id.id),
        #                     ('state', 'not in', ['draft','rejected'])]):
        #         raise ValidationError(_('Date %s for %s has been actualized!') % (rec.date,rec.employee_id.name))
        #     elif self.search([('date', '=', rec.date), ('id', '!=', rec.id), ('actual_id', '=', rec.actual_id.id),
        #                       ('employee_id', '=', rec.employee_id.id),]):
        #         raise ValidationError(_('Duplicate date %s for %s !') % (rec.date,rec.employee_id.name))
        return res

    @api.depends('actual_start_time', 'actual_end_time')
    def _compute_break_time(self):
        for rec in self:
            user_tz = rec.employee_id.tz or 'UTC'
            local = pytz.timezone(user_tz)
            emp_work_schedule = self.env['employee.working.schedule.calendar'].search(
                [('employee_id', '=', rec.employee_id.id), ('date_start', '=', rec.date)], limit=1)
            if emp_work_schedule:
                working_time = emp_work_schedule.working_hours
            else:
                working_time = rec.employee_id.resource_calendar_id
            wt_overtime_rule = working_time.overtime_rules_id
            week_working_day = working_time.week_working_day

            working_schedule_cal = self.env['employee.working.schedule.calendar'].search(
                [('employee_id', '=', rec.employee_id.id)])
            shortday_schedule_cal = self.env['employee.working.schedule.calendar'].search([('is_holiday', '=', True),
                                                                                        ('dayofweek', '=', 4)])

            day_dict = []
            for cal in working_schedule_cal:
                if cal.day_type != "day_off":
                    day_dict += [cal.date_start]

            shortday_dict = []
            for shortcal in shortday_schedule_cal:
                shortday_dict += [shortcal.date_start]

            if rec.actual_start_time > rec.actual_end_time:
                actual_hour1 = 24.0 - rec.actual_start_time
                actual_hour2 = rec.actual_end_time - 0.0
                actual_hours = actual_hour1 + actual_hour2
            else:
                actual_hours = rec.actual_end_time - rec.actual_start_time

            if wt_overtime_rule.use_government_rule:
                # government rule break time
                break_time_work_days = wt_overtime_rule.break_time_work_days
                break_time_offtime_five_days = wt_overtime_rule.break_time_offtime_five_days
                break_time_offtime_six_days = wt_overtime_rule.break_time_offtime_six_days
                break_time_off_public_holiday = wt_overtime_rule.break_time_off_public_holiday

                break_time = 0.0
                if rec.date in shortday_dict:
                    for breaks in break_time_off_public_holiday:
                        if actual_hours >= breaks.minimum_hours:
                            break_time = breaks.break_time
                elif rec.date in day_dict:
                    for breaks in break_time_work_days:
                        if actual_hours >= breaks.minimum_hours:
                            break_time = breaks.break_time
                elif rec.date not in day_dict and week_working_day == 5:
                    for breaks in break_time_offtime_five_days:
                        if actual_hours >= breaks.minimum_hours:
                            break_time = breaks.break_time
                elif rec.date not in day_dict and week_working_day == 6:
                    for breaks in break_time_offtime_six_days:
                        if actual_hours >= breaks.minimum_hours:
                            break_time = breaks.break_time

                rec.update({
                    'break_time': break_time
                })
            else:
                break_time_work_days = wt_overtime_rule.break_overtime_rules_line_ids
                break_time_offtime_five_days = wt_overtime_rule.break_off_five_ids
                break_time_offtime_six_days = wt_overtime_rule.break_off_six_ids
                break_time_off_public_holiday = wt_overtime_rule.break_off_public_ids

                break_time = 0
                if rec.date in shortday_dict:
                    for breaks in break_time_off_public_holiday:
                        if actual_hours >= breaks.minimum_hours:
                            break_time = breaks.break_time
                elif rec.date in day_dict:
                    for breaks in break_time_work_days:
                        if actual_hours >= breaks.minimum_hours:
                            break_time = breaks.break_time
                elif rec.date not in day_dict and week_working_day == 5:
                    for breaks in break_time_offtime_five_days:
                        if actual_hours >= breaks.minimum_hours:
                            break_time = breaks.break_time
                elif rec.date not in day_dict and week_working_day == 6:
                    for breaks in break_time_offtime_six_days:
                        if actual_hours >= breaks.minimum_hours:
                            break_time = breaks.break_time
                
                rec.update({
                    'break_time': break_time
                })

    @api.depends('actual_start_time', 'actual_end_time')
    def _compute_actual_hours(self):
        for rec in self:
            user_tz = rec.employee_id.tz or 'UTC'
            local = pytz.timezone(user_tz)
            emp_work_schedule = self.env['employee.working.schedule.calendar'].search(
                [('employee_id', '=', rec.employee_id.id), ('date_start', '=', rec.date)], limit=1)
            if emp_work_schedule:
                working_time = emp_work_schedule.working_hours
            else:
                working_time = rec.employee_id.resource_calendar_id
            wt_overtime_rule = working_time.overtime_rules_id
            week_working_day = working_time.week_working_day

            working_schedule_cal = self.env['employee.working.schedule.calendar'].search(
                [('employee_id', '=', rec.employee_id.id)])
            shortday_schedule_cal = self.env['employee.working.schedule.calendar'].search([('is_holiday', '=', True),
                                                                                           ('dayofweek', '=', 4)])

            day_dict = []
            for cal in working_schedule_cal:
                if cal.day_type != "day_off":
                    day_dict += [cal.date_start]

            shortday_dict = []
            for shortcal in shortday_schedule_cal:
                shortday_dict += [shortcal.date_start]

            works_day = wt_overtime_rule.works_day
            last_works_day_line = works_day.search([], order='id desc', limit=1)
            off_days_working = wt_overtime_rule.off_days_working
            last_off_days_working_line = off_days_working.search([], order='id desc', limit=1)
            off_days_working_per_week = wt_overtime_rule.off_days_working_per_week
            last_off_days_working_per_week_line = off_days_working_per_week.search([], order='id desc', limit=1)
            off_days_public_holiday = wt_overtime_rule.off_days_public_holiday
            last_off_days_public_holiday_line = off_days_public_holiday.search([], order='id desc', limit=1)

            if rec.actual_start_time > rec.actual_end_time:
                actual_hour1 = 24.0 - rec.actual_start_time
                actual_hour2 = rec.actual_end_time - 0.0
                actual_hours = actual_hour1 + actual_hour2
            else:
                actual_hours = rec.actual_end_time - rec.actual_start_time
            actual_mins = actual_hours * 60
            actual_hour, actual_min = divmod(actual_mins, 60)
            if actual_mins >= wt_overtime_rule.minimum_time:
                if wt_overtime_rule.use_government_rule:
                    if rec.date in shortday_dict:
                        if actual_hour > last_off_days_public_holiday_line.hour:
                            rec.update({
                                'actual_hours': last_off_days_public_holiday_line.hour - rec.break_time
                            })
                        else:
                            rec.update({
                                'actual_hours': actual_hours - rec.break_time
                            })
                    elif rec.date in day_dict:
                        if actual_hour > last_works_day_line.hour:
                            rec.update({
                                'actual_hours': last_works_day_line.hour - rec.break_time
                            })
                        else:
                            rec.update({
                                'actual_hours': actual_hours - rec.break_time
                            })
                    elif rec.date not in day_dict and week_working_day == 5:
                        if actual_hour > last_off_days_working_line.hour:
                            rec.update({
                                'actual_hours': last_off_days_working_line.hour - rec.break_time
                            })
                        else:
                            rec.update({
                                'actual_hours': actual_hours - rec.break_time
                            })
                    elif rec.date not in day_dict and week_working_day == 6:
                        if actual_hour > last_off_days_working_per_week_line.hour:
                            rec.update({
                                'actual_hours': last_off_days_working_per_week_line.hour - rec.break_time
                            })
                        else:
                            rec.update({
                                'actual_hours': actual_hours - rec.break_time
                            })

                    if wt_overtime_rule.overtime_rounding_ids:
                        actual_mins = rec.actual_hours * 60
                        actual_hour, actual_min = divmod(actual_mins, 60)
                        for val in wt_overtime_rule.overtime_rounding_ids:
                            if round(actual_min) >= val.minutes:
                                hours = actual_hour * 60
                                hours_minutes = (hours + val.rounding) / 60
                                rec.update({
                                    'actual_hours': hours_minutes
                                })
                else:
                    rec.update({
                        'actual_hours': actual_hours - rec.break_time
                    })

                    if wt_overtime_rule.overtime_rounding_ids:
                        actual_mins = rec.actual_hours * 60
                        actual_hour, actual_min = divmod(actual_mins, 60)
                        for val in wt_overtime_rule.overtime_rounding_ids:
                            if round(actual_min) >= val.minutes:
                                hours = actual_hour * 60
                                hours_minutes = (hours + val.rounding) / 60
                                rec.update({
                                    'actual_hours': hours_minutes
                                })
            else:
                rec.update({
                    'actual_hours': 0.0
                })

    @api.depends('date')
    def _get_name_of_day(self):
        for rec in self:
            if rec.date:
                name_day = rec.date.strftime("%A")
                rec.update({
                    'name_of_day': name_day
                })

    @api.constrains('actual_start_time','actual_end_time')
    def _check_actual_overtime_time(self):
        for rec in self:
            emp_work_schedule = self.env['employee.working.schedule.calendar'].search(
                [('employee_id', '=', rec.employee_id.id), ('date_start', '=', rec.date)], limit=1)
            if emp_work_schedule:
                if emp_work_schedule.hour_to > rec.actual_start_time >= emp_work_schedule.hour_from:
                    raise ValidationError("Your proposed start actual overtime time conflicts with your actual working hours. Please enter a time outside of your working hours.")
                if emp_work_schedule.hour_to > rec.actual_end_time > emp_work_schedule.hour_from:
                    raise ValidationError("Your proposed end actual overtime time conflicts with your actual working hours. Please enter a time outside of your working hours.")
                if rec.actual_end_time > emp_work_schedule.hour_from >= rec.actual_start_time and rec.actual_end_time >= emp_work_schedule.hour_to >= rec.actual_start_time:
                    raise ValidationError("Your proposed overtime conflicted with your actual working hours. Please enter a time outside of your working hours")

class Equip3HrOvertimeActualApprovalLine(models.Model):
    _name = 'hr.overtime.actual.approval.line'

    actual_id = fields.Many2one('hr.overtime.actual')
    sequence = fields.Integer('Sequence', compute="fetch_sl_no")
    approver_id = fields.Many2many('res.users', string="Approvers")
    approver_confirm = fields.Many2many('res.users', 'overtime_actual_line_user_approve_ids', 'user_id', string="Approvers confirm")
    approval_status = fields.Char('Approval Status')
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    timestamp = fields.Text('Timestamp')
    feedback = fields.Text('Feedback')
    minimum_approver = fields.Integer(default=1)
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'over_act_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='actual_id.state')

    @api.depends('actual_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.actual_id.actual_approval_line_ids:
            sl = sl + 1
            line.sequence = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len(rec.approver_id) < rec.minimum_approver and rec.actual_id.state == 'draft':
                rec.minimum_approver = len(rec.approver_id)
            if not rec.matrix_user_ids and rec.actual_id.state == 'draft':
                rec.matrix_user_ids = rec.approver_id

    def update_approver_state(self):
        for rec in self:
            if rec.actual_id.state == 'to_approve':
                if not rec.approver_confirm:
                    rec.approver_state = 'draft'
                elif rec.approver_confirm and rec.minimum_approver == len(rec.approver_confirm):
                    rec.approver_state = 'approved'
                else:
                    rec.approver_state = 'pending'

class Equip3HrOvertimeActualAttendanceLine(models.Model):
    _name = 'hr.overtime.actual.attendance.line'

    actual_id = fields.Many2one('hr.overtime.actual', ondelete="cascade")
    attendance_id = fields.Many2one('hr.attendance')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    check_in = fields.Datetime('Check In')
    check_out = fields.Datetime('Check Out')
    worked_hours = fields.Float(string='Worked Hours')
    attendance_status = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('leave', 'Leave')],
                                         string='Attendance Status')

