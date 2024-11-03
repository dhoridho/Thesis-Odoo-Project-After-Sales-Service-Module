# -*- coding: utf-8 -*-
import babel
from odoo import models, fields, api, tools, _
from datetime import datetime, timedelta, time
from odoo.exceptions import ValidationError
import requests
from lxml import etree
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
headers = {'content-type': 'application/json'}

class Equip3HrOvertimeRequest(models.Model):
    _name = 'hr.overtime.request'
    _description = 'HR Overtime Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    def name_get(self):
        result = []
        for rec in self:
            ttyme_start = datetime.combine(fields.Date.from_string(rec.period_start), time.min)
            ttyme_end = datetime.combine(fields.Date.from_string(rec.period_end), time.min)
            locale = self.env.context.get('lang') or 'en_US'
            period_start = tools.ustr(babel.dates.format_date(date=ttyme_start, format='dd MMM YYYY', locale=locale))
            period_end = tools.ustr(babel.dates.format_date(date=ttyme_end, format='dd MMM YYYY', locale=locale))
            name = rec.name + ' - ' + period_start + ' to ' + period_end
            result.append((rec.id, name))
        return result

    @api.returns('self')
    def _get_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False

    name = fields.Char('Number')
    request_type = fields.Selection([('by_employee', 'By Employee'),
                                     ('by_manager', 'By Manager')], default='', string='Request Type')
    employee_id = fields.Many2one('hr.employee', string='Employee', default=_get_employee, required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees', domain="[('parent_id', '=', employee_id)]")
    description = fields.Text('Description', required=True)
    period_start = fields.Date('Period Start', required=True)
    period_end = fields.Date('Period End', required=True)
    total_hours = fields.Float('Total Hours', store=True, readonly=True, compute='_get_total_hours')
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company,
                                 tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'),
                              ('rejected', 'Rejected')], default='draft', string='Status')
    request_line_ids = fields.One2many('hr.overtime.request.line', 'request_id')
    request_approval_line_ids = fields.One2many('hr.overtime.request.approval.line', 'request_id')
    is_hide_reject = fields.Boolean(default=True, compute='_get_is_hide')
    is_hide_approve = fields.Boolean(default=True, compute='_get_is_hide')
    user_approval_ids = fields.Many2many('res.users', compute="_is_hide_approve")
    overtime_wizard_state = fields.Char('OverTime Wizard State')
    approvers_ids = fields.Many2many('res.users', 'overtime_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', 'overtime_approved_user_rel', string='Approved by User')
    is_overtime_approval_matrix = fields.Boolean("Is Overtime Approval Matrix", compute='_compute_is_overtime_approval_matrix')
    state1 = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Submitted'), ('rejected', 'Rejected')],
                              string='Status', default='draft', tracking=False, copy=False, store=True, compute='_compute_state1')
    next_approver_ids = fields.Many2many('res.users', 'next_approver_users_overtime_rel', string='Next Approvers', compute="_compute_next_approver", store=True)

    @api.depends('request_approval_line_ids','request_approval_line_ids.approver_id','request_approval_line_ids.approver_confirm')
    def _compute_next_approver(self):
        for record in self:
            if record.request_approval_line_ids:
                sequence = [data.sequence for data in record.request_approval_line_ids.filtered(
                    lambda line: len(line.approver_confirm.ids) != line.minimum_approver)]
                if sequence:
                    minimum_sequence = min(sequence)
                    approve_user = record.request_approval_line_ids.filtered(lambda line: line.sequence == minimum_sequence)

                    if approve_user:
                        next_approver = []
                        for approver in approve_user:
                            for rec in approver.approver_id:
                                if rec.id not in approver.approver_confirm.ids:
                                    next_approver.append(rec.id)
                        record.next_approver_ids = next_approver
                    else:
                        record.next_approver_ids = False
                else:
                    record.next_approver_ids = False
            else:
                record.next_approver_ids = False
    
    def custom_overtime_request_to_approve_menu(self):
        views = [(self.env.ref('equip3_hr_attendance_overtime.overtime_requests_approval_tree_view').id, 'tree'),
                        (self.env.ref('equip3_hr_attendance_overtime.overtime_requests_approval_form_view').id, 'form')]
        if self.env.user.has_group('equip3_hr_attendance_overtime.group_overtime_all_approver'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Overtime Request to Approve',
                'res_model': 'hr.overtime.request',
                'view_mode': 'tree,form',
                'domain': [('state','=','to_approve')],
                'views':views,
                'help':"""<p class="oe_view_nocontent_create">
                    No data found.
                </p>"""
                
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Overtime Request to Approve',
                'res_model': 'hr.overtime.request',
                'view_mode': 'tree,form',
                'domain': [('state','=','to_approve'), ('next_approver_ids','in',self.env.user.ids)],
                'views':views,
                'help':"""<p class="oe_view_nocontent_create">
                    No data found.
                </p>"""
                
            }

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(Equip3HrOvertimeRequest, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(Equip3HrOvertimeRequest, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_is_overtime_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.overtime_approval_matrix')
            rec.is_overtime_approval_matrix = setting

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('hr.overtime.request')
        vals.update({'name': sequence})
        return super(Equip3HrOvertimeRequest, self).create(vals)

    @api.depends('request_approval_line_ids')
    def _is_hide_approve(self):
        for record in self:
            if record.request_approval_line_ids:
                sequence = [data.sequence for data in record.request_approval_line_ids.filtered(
                    lambda line: len(line.approver_confirm.ids) != line.minimum_approver)]
                if sequence:
                    minimum_sequence = min(sequence)
                    approve_user = record.request_approval_line_ids.filtered(lambda
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

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            ot_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.overtime_approval_matrix')
            if ot_setting:
                setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.approval_method')
                if record.request_type == 'by_employee':
                    if record.employee_id:
                        record.employee_ids = [(4, record.employee_id.id)]
                        if record.request_approval_line_ids:
                            remove = []
                            for line in record.request_approval_line_ids:
                                remove.append((2, line.id))
                            record.request_approval_line_ids = remove
                        if setting == 'employee_hierarchy':
                            record.request_approval_line_ids = self.approval_by_hierarchy(record)
                            self.app_list_overtime_emp_by_hierarchy()
                        else:
                            self.approval_by_matrix(record)

                elif record.request_type == 'by_manager':
                    if record.request_approval_line_ids:
                        remove = []
                        for line in record.request_approval_line_ids:
                            remove.append((2, line.id))
                        record.request_approval_line_ids = remove
                    if setting == 'employee_hierarchy':
                        record.request_approval_line_ids = self.approval_by_hierarchy(record)
                        self.app_list_overtime_emp_by_hierarchy()
                    else:
                        self.approval_by_matrix(record)

    def app_list_overtime_emp_by_hierarchy(self):
        for overtime in self:
            app_list = []
            for line in overtime.request_approval_line_ids:
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
            record.request_approval_line_ids = data_approvers
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
                record.request_approval_line_ids = data_approvers
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
                    record.request_approval_line_ids = data_approvers

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

    def get_manager_hierarchy(self, overtime, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(overtime, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    @api.onchange('request_type', 'period_start', 'period_end', 'employee_ids')
    def onchange_period(self):
        if self.request_type == 'by_employee':
            if (not self.employee_id) or (not self.period_start) or (not self.period_end) or (not self.request_type):
                return
        elif self.request_type == 'by_manager':
            if (not self.period_start) or (not self.period_end) or (not self.request_type):
                return

        period_start = self.period_start
        period_end = self.period_end
        delta = period_end - period_start
        days = [period_start + timedelta(days=i) for i in range(delta.days + 1)]

        ttyme = datetime.combine(fields.Date.from_string(period_start), time.min)
        ttyme_end = datetime.combine(fields.Date.from_string(period_end), time.min)
        locale = self.env.context.get('lang') or 'en_US'
        self.description = _('Overtime request for period: %s to %s') % (
            tools.ustr(babel.dates.format_date(date=ttyme, format='dd MMM YYYY', locale=locale)), tools.ustr(babel.dates.format_date(date=ttyme_end, format='dd MMM YYYY', locale=locale)))

        request_line = []
        for date in days:
            if self.request_type == 'by_employee':
                input_data = {
                    'employee_id': self.employee_id.id,
                    'request_type': self.request_type,
                    'date': date,
                    'request_id': self.id,
                }
                request_line += [input_data]
            elif self.request_type == 'by_manager':
                for emp in self.employee_ids.ids:
                    input_data = {
                        'employee_id': emp,
                        'request_type': self.request_type,
                        'date': date,
                        'request_id': self.id,
                    }
                    request_line += [input_data]

        request_lines = self.request_line_ids.browse([])
        for r in request_line:
            request_lines += request_lines.new(r)
        self.request_line_ids = request_lines

    def confirm(self):
        ot_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.overtime_approval_matrix')
        for rec in self:
            period_start = rec.period_start
            period_end = rec.period_end
            delta = period_end - period_start
            days = [period_start + timedelta(days=i) for i in range(delta.days + 1)]
            start_of_week_data = []
            for date in days:
                start_of_week_period = date - timedelta(days=date.weekday())
                if start_of_week_period not in start_of_week_data:
                    start_of_week_data.append(start_of_week_period)
            
            for line in rec.request_line_ids:
                # other_request = self.env['hr.overtime.request.line'].search(
                #         [('employee_id', '=', line.employee_id.id),('date','=',line.date),('state','in',['to_approve','approved'])],limit=1)
                # if other_request:
                #     raise ValidationError(_('Date %s for %s has been requested!') % (other_request.date,other_request.employee_id.name))
                
                working_time = line.employee_id.resource_calendar_id
                wt_overtime_rule = working_time.overtime_rules_id
                if wt_overtime_rule.is_use_ovt_limit:
                    ovt_limit_day_mins = wt_overtime_rule.ovt_limit_day * 60
                    ovt_limit_day_hour, ovt_limit_day_min = divmod(ovt_limit_day_mins, 60)
                    actual_line_day = self.env['hr.overtime.actual.line'].search(
                            [('employee_id', '=', line.employee_id.id),('date','=',line.date),('state','in',['approved'])],limit=1)
                    if actual_line_day:
                        total_hours = line.number_of_hours + actual_line_day.actual_hours
                        remaining_hours = wt_overtime_rule.ovt_limit_day - actual_line_day.actual_hours
                    else:
                        total_hours = line.number_of_hours
                        remaining_hours = wt_overtime_rule.ovt_limit_day
                    remaining_hours_mins = remaining_hours * 60
                    remaining_hours_mins_hour, remaining_hours_mins_min = divmod(remaining_hours_mins, 60)
                    if total_hours > wt_overtime_rule.ovt_limit_day:
                        raise ValidationError(_('You can only apply for %s hours %s minutes of overtime per Day. The remaining Limit for your submission on this date %s for %s is %s hour %s minute.') % (int(ovt_limit_day_hour),int(ovt_limit_day_min),line.date,line.employee_id.name,int(remaining_hours_mins_hour),int(remaining_hours_mins_min)))
                else:
                    req_other_line = rec.request_line_ids.filtered(lambda r: r.id != line.id and r.employee_id == line.employee_id and r.date == line.date)
                    for rec_other in req_other_line:
                        if line.end_time > rec_other.start_time > line.start_time or line.end_time > rec_other.end_time > line.start_time:
                            raise ValidationError("One of your overtime request lines collides with another line. Please enter a time that does not collide with each other")
                    rec_line_approve = self.env['hr.overtime.request.line'].search(
                            [('employee_id', '=', line.employee_id.id),('date','=',line.date),('state','in',['to_approve','approved'])])
                    for linex in rec_line_approve:
                        if line.end_time >= linex.start_time >= line.start_time or line.end_time >= linex.end_time >= line.start_time:
                            raise ValidationError("This overtime request conflicted with your other overtime requests. Please double-check your overtime request and ensure that the hours you submit aren't in conflict with previous requests")
            if rec.request_type == "by_employee":
                working_time = rec.employee_id.resource_calendar_id
                wt_overtime_rule = working_time.overtime_rules_id
                if wt_overtime_rule.is_use_ovt_limit:
                    for week in start_of_week_data:
                        end_of_week = week + timedelta(days=6)
                        sum_req_hours = 0
                        for line in rec.request_line_ids:
                            if line.date >= week and line.date <= end_of_week:
                                sum_req_hours += line.number_of_hours
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
                        req_line = rec.request_line_ids.filtered(lambda r: r.employee_id == emp)
                        for week in start_of_week_data:
                            end_of_week = week + timedelta(days=6)
                            sum_req_hours = 0
                            for line in req_line:
                                if line.date >= week and line.date <= end_of_week:
                                    sum_req_hours += line.number_of_hours
                            actual_line_week = self.env['hr.overtime.actual.line'].search(
                                    [('employee_id', '=', line.employee_id.id),('date','>=',week),('date','<=',end_of_week),('state','in',['to_approve','approved'])])
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
            for line in rec.request_line_ids:
                line.write({'state': 'to_approve'})
            if ot_setting:
                if not rec.request_approval_line_ids:
                    rec.state = "approved"
                    # rec.message_post(body=_('Periods Status: Draft -> Approved'))
                else:
                    rec.state = "to_approve"
                    # rec.message_post(body=_('Periods Status: Draft -> To Approve'))

                rec.approver_mail()
                rec.approver_wa_template()
                for line in rec.request_approval_line_ids:
                    line.write({'approver_state': 'draft'})
            else:
                rec.write({'state': 'approved'})
                for line in rec.request_line_ids:
                    line.write({'state': 'approved'})

    def approve(self):
        self.update({
            'overtime_wizard_state': 'approved',
        })
        self.request_approval_line_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.overtime.approval.wizard',
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
        self.request_approval_line_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.overtime.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_overtime_id':self.id,
                        'default_state':self.overtime_wizard_state},
        }

    @api.depends('request_line_ids.number_of_hours')
    def _get_total_hours(self):
        for rec in self:
            total_hours = 0.0
            for line in rec.request_line_ids:
                total_hours += line.number_of_hours
            rec.update({
                'total_hours': total_hours,
            })

    @api.constrains('request_line_ids')
    def _check_overtime_reason(self):
        for rec in self:
            for line in rec.request_line_ids:
                if not line.overtime_reason:
                    raise ValidationError(_("""You must filled overtime reason."""))
                if not line.date:
                    raise ValidationError(_("""You must filled overtime date."""))

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_attendance_overtime', 'overtime_requests_approval_menu')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_attendance_overtime', 'overtime_requests_approval_act_window')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.overtime.request&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.request_approval_line_ids:
                matrix_line = sorted(rec.request_approval_line_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.request_approval_line_ids[len(matrix_line)]
                for user in approver.approver_id:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_attendance_overtime',
                            'email_template_approver_of_overtime_req')[1]
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
            if rec.request_approval_line_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_attendance_overtime',
                        'email_template_approved_overtime')[1]
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
            if rec.request_approval_line_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_attendance_overtime',
                        'email_template_rejection_of_overtime_req')[1]
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
            template = self.env.ref('equip3_hr_attendance_overtime.overtime_approver_wa_template')
            wa_sender = waParam()
            if template:
                if self.request_approval_line_ids:
                    matrix_line = sorted(self.request_approval_line_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.request_approval_line_ids[len(matrix_line)]
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
            template = self.env.ref('equip3_hr_attendance_overtime.overtime_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.request_approval_line_ids:
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
            template = self.env.ref('equip3_hr_attendance_overtime.overtime_rejected_wa_template')
            url = self.get_url(self)
            wa_sender = waParam()
            if template:
                if self.request_approval_line_ids:
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
            template = self.env.ref('equip3_hr_attendance_overtime.overtime_approver_wa_template')
            wa_sender = waParam()
            if template:
                if rec.request_approval_line_ids:
                    matrix_line = sorted(rec.request_approval_line_ids.filtered(lambda r: r.is_approve == True))
                    approver = rec.request_approval_line_ids[len(matrix_line)]
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
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_overtime.number_of_repetitions_overtime'))
        overtime_approve = self.search([('state', '=', 'to_approve')])
        for rec in overtime_approve:
            if rec.request_approval_line_ids:
                matrix_line = sorted(rec.request_approval_line_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.request_approval_line_ids[len(matrix_line)]
                for user in approver.approver_id:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_attendance_overtime',
                            'email_template_approver_of_overtime_req')[1]
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
                        query_statement = """UPDATE hr_overtime_request_approval_line set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                        self.get_auto_follow_up_approver_wa_template(rec)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approver_confirm and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE hr_overtime_request_approval_line set repetition_follow_count = %s WHERE id = %s """
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
            if rec.request_approval_line_ids:
                matrix_line = sorted(rec.request_approval_line_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.request_approval_line_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in approver.approver_confirm.ids and user.user_delegation_id.id not in approver.approver_confirm.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_attendance_overtime',
                                    'email_template_approver_of_overtime_req')[1]
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

class Equip3HrOvertimeRequestLine(models.Model):
    _name = 'hr.overtime.request.line'
    _order = 'create_date desc'

    @api.returns('self')
    def _get_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False

    request_id = fields.Many2one('hr.overtime.request')
    request_type = fields.Selection([('by_employee', 'By Employee'),
                                     ('by_manager', 'By Manager')], default='', string='Request Type')
    employee_id = fields.Many2one('hr.employee', string='Employee', default=_get_employee, required=True)
    overtime_reason = fields.Char('Overtime Reason')
    date = fields.Date('Date', readonly=True)
    name_of_day = fields.Char('Name of Day', store=True, readonly=True, compute='_get_name_of_day')
    start_time = fields.Float('Start Time', required=True)
    end_time = fields.Float('End Time', required=True)
    number_of_hours = fields.Float('Number of Hours', store=True, readonly=True, compute='_compute_number_of_hours')
    state = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'),
                              ('rejected', 'Rejected')], default='draft', string='Status')
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(Equip3HrOvertimeRequestLine, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(Equip3HrOvertimeRequestLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(Equip3HrOvertimeRequestLine, self).fields_view_get(
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

    @api.onchange('request_type')
    def _onchange_request_type(self):
        if self.request_type == "by_manager":
            self.employee_id = False

    @api.onchange('start_time', 'end_time')
    def _onchange_hours(self):
        self.start_time = min(self.start_time, 23.99)
        self.start_time = max(self.start_time, 0.0)
        self.end_time = min(self.end_time, 23.99)
        self.end_time = max(self.end_time, 0.0)

    @api.depends('start_time', 'end_time')
    def _compute_number_of_hours(self):
        for rec in self:
            if rec.start_time > rec.end_time:
                hour1 = 24.0 - rec.start_time
                hour2 = rec.end_time - 0.0
                number_of_hours = hour1 + hour2
            else:
                number_of_hours = rec.end_time - rec.start_time
            rec.update({
                'number_of_hours': number_of_hours
            })

    @api.constrains('start_time','end_time')
    def _check_req_overtime_time(self):
        for rec in self:
            emp_work_schedule = self.env['employee.working.schedule.calendar'].search(
                [('employee_id', '=', rec.employee_id.id), ('date_start', '=', rec.date)], limit=1)
            if emp_work_schedule:
                if emp_work_schedule.hour_to > rec.start_time >= emp_work_schedule.hour_from:
                    raise ValidationError("Your proposed start overtime time conflicts with your actual working hours. Please enter a time outside of your working hours.")
                if emp_work_schedule.hour_to >= rec.end_time >= emp_work_schedule.hour_from:
                    raise ValidationError("Your proposed end overtime time conflicts with your actual working hours. Please enter a time outside of your working hours.")
                if rec.end_time > emp_work_schedule.hour_from >= rec.start_time and rec.end_time >= emp_work_schedule.hour_to >= rec.start_time:
                    raise ValidationError("Your proposed overtime conflicted with your actual working hours. Please enter a time outside of your working hours")

    @api.depends('date')
    def _get_name_of_day(self):
        for rec in self:
            if rec.date:
                name_day = rec.date.strftime("%A")
                rec.update({
                    'name_of_day': name_day
                })

class Equip3HrOvertimeRequestApprovalLine(models.Model):
    _name = 'hr.overtime.request.approval.line'

    request_id = fields.Many2one('hr.overtime.request')
    sequence = fields.Integer('Sequence', compute="fetch_sl_no")
    approver_id = fields.Many2many('res.users', string="Approvers")
    approver_confirm = fields.Many2many('res.users', 'overtime_line_user_approve_ids', 'user_id', string="Approvers confirm")
    approval_status = fields.Text('Approval Status')
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    timestamp = fields.Text('Timestamp')
    feedback = fields.Text('Feedback')
    minimum_approver = fields.Integer(default=1)
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'over_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='request_id.state')


    @api.depends('request_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.request_id.request_approval_line_ids:
            sl = sl + 1
            line.sequence = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len(rec.approver_id) < rec.minimum_approver and rec.request_id.state == 'draft':
                rec.minimum_approver = len(rec.approver_id)
            if not rec.matrix_user_ids and rec.request_id.state == 'draft':
                rec.matrix_user_ids = rec.approver_id

    def update_approver_state(self):
        for rec in self:
            if rec.request_id.state == 'to_approve':
                if not rec.approver_confirm:
                    rec.approver_state = 'draft'
                elif rec.approver_confirm and rec.minimum_approver == len(rec.approver_confirm):
                    rec.approver_state = 'approved'
                else:
                    rec.approver_state = 'pending'
