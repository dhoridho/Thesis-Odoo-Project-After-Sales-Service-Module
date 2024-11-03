# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import pytz
from odoo.exceptions import ValidationError
from pytz import timezone
from dateutil.relativedelta import relativedelta
import requests
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
headers = {'content-type': 'application/json'}

class HrAttendanceChange(models.Model):
    _name = 'hr.attendance.change'
    _description = 'Attendance Change Reuest'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    
    

    @api.model
    def default_get(self, fields):
        res = super(HrAttendanceChange, self).default_get(fields)
        employees = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        res['employee_id'] = employees.id
        return res

    @api.model
    def create(self, vals):
        sequence_no = self.env['ir.sequence'].next_by_code('hr.attendance.change')
        vals.update({'name': sequence_no})
        return super(HrAttendanceChange, self).create(vals)

    name = fields.Char(string="Name", readonly=True, required=True, copy=False, default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    domain_employee_ids = fields.Many2many('hr.employee',string="Employee Domain",compute='_compute_employee_ids')
    is_readonly = fields.Boolean(compute='_compute_read_only')
    request_date_from = fields.Date('Request Start Date', required=True, tracking=True)
    request_date_to = fields.Date('Request End Date', required=True, tracking=True)
    attachment = fields.Binary('Attachment', tracking=True)
    attachment_name = fields.Char(string='Attachment Name')
    state = fields.Selection([("draft", "Draft"),
                              ("to_approve", "To Approve"),
                              ("approved", "Approved"),
                              ("refused", "Rejected")
                              ], string='Status', default="draft", tracking=True)
    attendance_change_line_ids = fields.One2many('hr.attendance.change.line', 'hr_attendance_change_id',
                                                 string='Attendance Line Ids', tracking=True)
    # is_approver = fields.Boolean('Is Approver', compute='_compute_is_approver', default=False)

    attendance_change_user_ids = fields.One2many('attendance.change.approver.user', 'attendance_change_approver_id',
                                                string='Approver')
    approvers_ids = fields.Many2many('res.users', 'attendance_change_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    is_attendance_change_approval_matrix = fields.Boolean("Is Attendance Change Approval Matrix",
                                                          compute='_compute_is_attendance_change_approval_matrix')
    state1 = fields.Selection([("draft", "Draft"), ("to_approve", "To Approve"), ("approved", "Submitted"), ("refused", "Rejected")],
                              string='Status', default='draft', tracking=False, copy=False, store=True, compute='_compute_state1')

    def unlink(self):
        for rec in self:
            if rec.state in ('approved'):
                raise ValidationError(_('You cannot delete an Attendance Change Request that has been Approved.'))
        return super(HrAttendanceChange, self).unlink()
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrAttendanceChange, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrAttendanceChange, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_is_attendance_change_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.attendance_approval_matrix')
            rec.is_attendance_change_approval_matrix = setting
    
    @api.depends('employee_id')
    def _compute_read_only(self):
        for record in self:
            if self.env.user.has_group('hr_attendance.group_hr_attendance') and not self.env.user.has_group('hr_attendance.group_hr_attendance_user'):
                record.is_readonly = True
            else:
                record.is_readonly = False
                
    @api.depends('employee_id')
    def _compute_employee_ids(self):
        for record in self:
            employee_ids = []
            if self.env.user.has_group('hr_attendance.group_hr_attendance_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_attendance_hr_manager'):
                my_employee = self.env['hr.employee'].sudo().search([('user_id','=',self.env.user.id),('company_id','in',self.env.company.ids)])
                if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(my_employee.id)
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
                record.domain_employee_ids = [(6,0,employee_ids)]
            else:
                all_employee = self.env['hr.employee'].sudo().search([('company_id','in',self.env.company.ids)])
                for data_employee in all_employee:
                    employee_ids.append(data_employee.id)
                record.domain_employee_ids = [(6,0,employee_ids)]
    
    def custom_menu_request(self):
            # views = [(self.env.ref('bi_employee_travel_managment.view_travel_req_tree').id, 'tree'),
        #              (self.env.ref('bi_employee_travel_managment.view_travel_req_form').id, 'form')]
        # search_view_id = self.env.ref("equip3_hr_holidays_extend.view_my_leave_cancel_tree")
        if  self.env.user.has_group('hr_attendance.group_hr_attendance_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_attendance_hr_manager'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id','=',self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Attendance Change Request',
                    'res_model': 'hr.attendance.change',
                    'target':'current',
                    'view_mode': 'tree,form',
                    # 'views':views,
                    'domain': [('employee_id', 'in', employee_ids)],
                    'context':{},
                    'help':"""<p class="o_view_nocontent_smiling_face">
                        Create a new Attendance Change Request
                    </p>""",
                    # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                    # 'search_view_id':search_view_id.id,
                    
                }
        
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Attendance Change Request',
                'res_model': 'hr.attendance.change',
                'target':'current',
                'view_mode': 'tree,form',
                'domain': [],
                'help':"""<p class="o_view_nocontent_smiling_face">
                    Create a new Attendance Change Request
                </p>""",
                'context':{},
                # 'views':views,
                # 'search_view_id':search_view_id.id,
            }
    
    
    def custom_menu(self):
        views = [(self.env.ref('equip3_hr_attendance_extend.view_hr_working_schedule_exchange_tree').id, 'tree'),
                    (self.env.ref('equip3_hr_attendance_extend.view_hr_working_schedule_exchange_form').id, 'form')]
        if  self.env.user.has_group('hr_attendance.group_hr_attendance') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_attendance_hr_manager'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'My Attendance Change Request',
                'res_model': 'hr.attendance.change',
                'view_mode': 'tree,form',
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                # 'search_view_id':search_view_id.id,
                
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'My Attendance Change Request',
                'res_model': 'hr.attendance.change',
                'view_mode': 'tree,form',
                # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                # 'search_view_id':search_view_id.id,
                
            }

    @api.onchange('employee_id', 'request_date_from')
    def onchange_approver_user(self):
        for attendance_change in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.attendance_approval_matrix')
            if setting:
                if attendance_change.attendance_change_user_ids:
                    remove = []
                    for line in attendance_change.attendance_change_user_ids:
                        remove.append((2, line.id))
                    attendance_change.attendance_change_user_ids = remove
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_attendance_extend.attendance_type_approval')
                if setting == 'employee_hierarchy':
                    attendance_change.attendance_change_user_ids = self.attendance_change_emp_by_hierarchy(attendance_change)
                    self.app_list_attendance_change_emp_by_hierarchy()
                if setting == 'approval_matrix':
                    self.attendance_change_approval_by_matrix(attendance_change)

    def attendance_change_emp_by_hierarchy(self, attendance_change):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(attendance_change, attendance_change.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, attendance_change, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.attendance_level')
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
                self.get_manager(attendance_change, employee_manager['parent_id'], data, approval_ids, seq)
                break

        return approval_ids

    def get_manager_hierarchy(self, attendance_change, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(attendance_change, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def app_list_attendance_change_emp_by_hierarchy(self):
        for attendance_change in self:
            app_list = []
            for line in attendance_change.attendance_change_user_ids:
                app_list.append(line.user_ids.id)
            attendance_change.approvers_ids = app_list

    def attendance_change_approval_by_matrix(self, attendance_change):
        app_list = []
        approval_matrix = self.env['hr.attendance.approval.matrix'].search(
            [('apply_to', '=', 'by_employee')])
        matrix = approval_matrix.filtered(lambda line: attendance_change.employee_id.id in line.employee_ids.ids)
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
                    approvers = self.get_manager_hierarchy(attendance_change, attendance_change.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            attendance_change.approvers_ids = app_list
            attendance_change.attendance_change_user_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.attendance.approval.matrix'].search(
                [('apply_to', '=', 'by_job_position')])
            matrix = approval_matrix.filtered(lambda line: attendance_change.job_id.id in line.job_ids.ids)
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
                        approvers = self.get_manager_hierarchy(attendance_change, attendance_change.employee_id, data,
                                                               manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                attendance_change.approvers_ids = app_list
                attendance_change.attendance_change_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.attendance.approval.matrix'].search(
                    [('apply_to', '=', 'by_department')])
                matrix = approval_matrix.filtered(lambda line: attendance_change.department_id.id in line.department_ids.ids)
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
                            approvers = self.get_manager_hierarchy(attendance_change, attendance_change.employee_id,
                                                                   data,
                                                                   manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    attendance_change.approvers_ids = app_list
                    attendance_change.attendance_change_user_ids = data_approvers

    @api.depends('state', 'employee_id', 'request_date_from')
    def _compute_is_approver(self):
        for attendance_change in self:
            if attendance_change.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_attendance_extend.attendance_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_attendance_extend.attendance_level')
                app_level = int(setting_level)
                current_user = attendance_change.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(attendance_change.attendance_change_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(attendance_change.attendance_change_user_ids)
                    if app < app_level and app < a:
                        if current_user in attendance_change.attendance_change_user_ids[app].user_ids:
                            attendance_change.is_approver = True
                        else:
                            attendance_change.is_approver = False
                    else:
                        attendance_change.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(attendance_change.attendance_change_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(attendance_change.attendance_change_user_ids)
                    if app < a:
                        for line in attendance_change.attendance_change_user_ids[app]:
                            if current_user in line.user_ids:
                                attendance_change.is_approver = True
                            else:
                                attendance_change.is_approver = False
                    else:
                        attendance_change.is_approver = False

                else:
                    attendance_change.is_approver = False
            else:
                attendance_change.is_approver = False

    # def _compute_is_approver(self):
    #     for rec in self:
    #         current_user = rec.env.user
    #         if rec.employee_id.parent_id.user_id == current_user and rec.state == 'to_approve':
    #             rec.is_approver = True
    #         else:
    #             rec.is_approver = False

    @api.onchange('request_date_from', 'request_date_to', 'employee_id')
    def onchange_fetch_attendance(self):
        for rec in self:
            if rec.attendance_change_line_ids:
                remove = []
                for line in rec.attendance_change_line_ids:
                    remove.append((2, line.id))
                rec.attendance_change_line_ids = remove
            if rec.request_date_from and rec.request_date_to:
                fmt = '%Y-%m-%d'
                d1 = datetime.strptime(str(rec.request_date_from), fmt)
                d2 = datetime.strptime(str(rec.request_date_to), fmt)
                delta = d2 - d1
                for i in range(0, delta.days + 1):
                    between = d1 + timedelta(days=i)
                    date_vals = [(0, 0, {'hr_attendance_change_id': self.id, 'date': between,
                                         'resource_calendar_id': rec.employee_id.resource_calendar_id.id})]
                    rec.attendance_change_line_ids = date_vals
                for hr_att in rec.env['hr.attendance'].search(
                        [('employee_id', '=', rec.employee_id.id), ('start_working_date', '>=', rec.request_date_from),
                         ('start_working_date', '<=', rec.request_date_to)]):
                    for line in rec.attendance_change_line_ids:
                        d3 = datetime.strptime(str(line.date), fmt)
                        if hr_att.check_in and line.date == hr_att.start_working_date:
                            # Checkin cnverting into timezone pick time
                            now_in_utc = pytz.utc.localize(hr_att.check_in)
                            tz_in = pytz.timezone(rec.env.user.tz or 'UTC')
                            now_in_tz = now_in_utc.astimezone(tz_in)
                            time_3 = str(now_in_tz)
                            time_4 = time_3[-14:][:-8]
                            # Checkin cnverting into timezone pick date
                            pick_date_checkin = time_3[:-6][:-9]
                            d4 = datetime.strptime(str(pick_date_checkin), fmt)
                            # Checkin string to float convert
                            vals = time_4.split(':')
                            t, hours = divmod(float(vals[0]), 24)
                            t, minutes = divmod(float(vals[1]), 60)
                            minutes = minutes / 60.0
                            convert_time = hours + minutes
                            line.update({
                                'check_in': convert_time,
                            })
                        if hr_att.check_out and line.date == hr_att.start_working_date:
                            # Checkout cnverting into timezone
                            now_out_utc = pytz.utc.localize(hr_att.check_out)
                            tz_out = pytz.timezone(self.env.user.tz or 'UTC')
                            now_out_tz = now_out_utc.astimezone(tz_out)
                            time_5 = str(now_out_tz)
                            time_6 = time_5[-14:][:-8]
                            # Checkin string to float convert
                            vals_out = time_6.split(':')
                            t, hours_out = divmod(float(vals_out[0]), 24)
                            t, minutes_out = divmod(float(vals_out[1]), 60)
                            minutes_out = minutes_out / 60.0
                            convert_time_out = hours_out + minutes_out
                            line.update({
                                'check_out': convert_time_out,
                            })
                        if hr_att and line.date == hr_att.start_working_date:
                            line.update({
                                'hr_attendance_id': hr_att.id,
                                'checkin_status':hr_att.checkin_status,
                                'checkout_status':hr_att.checkout_status,
                                'attendance_status': hr_att.attendance_status,
                            })

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_attendance_extend', 'hr_attendance_change_manager_menu')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_attendance_extend', 'hr_attendance_change_action_manager')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.holidays&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.attendance_change_user_ids:
                matrix_line = sorted(rec.attendance_change_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.attendance_change_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_attendance_extend',
                            'email_template_attendance_change_request_approval')[1]
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
                    if self.request_date_from:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(self.request_date_from).strftime('%d/%m/%Y')})
                    if self.request_date_to:
                        ctx.update(
                            {'date_to': fields.Datetime.from_string(self.request_date_to).strftime('%d/%m/%Y')})
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                              force_send=True)
                break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.attendance_change_user_ids:
                for rec in rec.attendance_change_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.user_ids:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_attendance_extend',
                                'email_template_attendance_change_approved')[1]
                        except ValueError:
                            template_id = False
                        ctx = self._context.copy()
                        url = self.get_url(self)
                        ctx.update({
                            'email_from': self.env.user.email,
                            'email_to': self.employee_id.user_id.email,
                            'url': url,
                            'name': self.name,
                            'emp_name': self.employee_id.name,
                        })
                        if self.request_date_from:
                            ctx.update(
                                {'date_from': fields.Datetime.from_string(self.request_date_from).strftime('%d/%m/%Y')})
                        if self.request_date_to:
                            ctx.update(
                                {'date_to': fields.Datetime.from_string(self.request_date_to).strftime('%d/%m/%Y')})
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                    break

    def reject_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.attendance_change_user_ids:
                for rec in rec.attendance_change_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.user_ids:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_attendance_extend',
                                'email_template_attendance_change_reject')[1]
                        except ValueError:
                            template_id = False
                        ctx = self._context.copy()
                        ctx.pop('default_state')
                        url = self.get_url(self)
                        ctx.update({
                            'email_from': self.env.user.email,
                            'email_to': self.employee_id.user_id.email,
                            'url': url,
                            'name': self.name,
                            'emp_name': self.employee_id.name,
                        })
                        if self.request_date_from:
                            ctx.update(
                                {'date_from': fields.Datetime.from_string(self.request_date_from).strftime('%d/%m/%Y')})
                        if self.request_date_to:
                            ctx.update(
                                {'date_to': fields.Datetime.from_string(self.request_date_to).strftime('%d/%m/%Y')})
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                    break

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(self)
        if send_by_wa:
            wa_sender = waParam()
            template = self.env.ref('equip3_hr_attendance_extend.attendance_approver_wa_template')
            if template:
                if self.attendance_change_user_ids:
                    matrix_line = sorted(self.attendance_change_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.attendance_change_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", self.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.name)
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${start_date}" in string_test:
                            string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                                self.request_date_from).strftime('%d/%m/%Y'))
                        if "${end_date}" in string_test:
                            string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                                self.request_date_to).strftime('%d/%m/%Y'))
                        if "${br}" in string_test:
                            string_test = string_test.replace("${br}", f"\n")
                        if "${url}" in string_test:
                            string_test = string_test.replace("${url}", url)
                        phone_num = str(user.mobile_phone)
                        if "+" in phone_num:
                            phone_num = int(phone_num.replace("+", ""))
                        
                        wa_sender.set_wa_string(string_test,template._name,template_id=template)
                        wa_sender.send_wa(phone_num)

        #                 param = {'body': string_test, 'phone': phone_num}
        #                 domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
        #                 token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
        #                 try:
        #                     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
        #                 except ConnectionError:
        #                     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_extend.attendance_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.attendance_change_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.request_date_from).strftime('%d/%m/%Y'))
                    if "${end_date}" in string_test:
                        string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                            self.request_date_to).strftime('%d/%m/%Y'))
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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_extend.attendance_rejected_wa_template')
            url = self.get_url(self)
            wa_sender = waParam()
            if template:
                if self.attendance_change_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.request_date_from).strftime('%d/%m/%Y'))
                    if "${end_date}" in string_test:
                        string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                            self.request_date_to).strftime('%d/%m/%Y'))
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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(rec)
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_extend.attendance_approver_wa_template')
            wa_sender = waParam()
            if template:
                if rec.attendance_change_user_ids:
                    matrix_line = sorted(rec.attendance_change_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = rec.attendance_change_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", rec.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", rec.name)
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${start_date}" in string_test:
                            string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                                rec.request_date_from).strftime('%d/%m/%Y'))
                        if "${end_date}" in string_test:
                            string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                                rec.request_date_to).strftime('%d/%m/%Y'))
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
        number_of_repititions_attendance = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.number_of_repetitions_attendance'))
        attendance_approve = self.search([('state', '=', 'to_approve')])
        for rec in attendance_approve:
            if rec.attendance_change_user_ids:
                matrix_line = sorted(rec.attendance_change_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.attendance_change_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_attendance_extend',
                            'email_template_attendance_change_request_approval')[1]
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
                    if rec.request_date_from:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(rec.request_date_from).strftime('%d/%m/%Y')})
                    if rec.request_date_to:
                        ctx.update(
                            {'date_to': fields.Datetime.from_string(rec.request_date_to).strftime('%d/%m/%Y')})
                    if not approver.is_auto_follow_approver:
                        count = number_of_repititions_attendance - 1
                        query_statement = """UPDATE attendance_change_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                        self.get_auto_follow_up_approver_wa_template(rec)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE attendance_change_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
                            self.get_auto_follow_up_approver_wa_template(rec)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        attendance_approve = self.search([('state', '=', 'to_approve')])
        for rec in attendance_approve:
            if rec.attendance_change_user_ids:
                matrix_line = sorted(rec.attendance_change_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.attendance_change_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_attendance_extend',
                                    'email_template_attendance_change_request_approval')[1]
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
                            if rec.request_date_from:
                                ctx.update(
                                    {'date_from': fields.Datetime.from_string(rec.request_date_from).strftime('%d/%m/%Y')})
                            if rec.request_date_to:
                                ctx.update(
                                    {'date_to': fields.Datetime.from_string(rec.request_date_to).strftime('%d/%m/%Y')})
                            approver.update({
                                'user_ids': [(4, user.user_delegation_id.id)],
                                'is_delegation_mail_sent': True,
                            })
                            rec.update({
                                'approvers_ids': [(4, user.user_delegation_id.id)],
                            })
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

    def action_confirm(self):
        setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.attendance_approval_matrix')
        for rec in self:
            setting_past_date_limit = int(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.past_date_limit'))
            past_date_limit_days = date.today() - relativedelta(days=setting_past_date_limit)
            if setting_past_date_limit != 0:
                if rec.request_date_from and rec.request_date_from < past_date_limit_days:
                    raise ValidationError("You can only submit an Attendance Change Request for the past %s days." % setting_past_date_limit)
            
            for line in rec.attendance_change_line_ids:
                working_calendar = rec.env['employee.working.schedule.calendar'].search([('employee_id', '=', rec.employee_id.id), ('date_start', '=', line.date)], limit=1)
                if not working_calendar:
                    raise ValidationError("Working Calendar for %s not found." % line.date)
                else:
                    if line.hr_attendance_id and line.check_in_correction:
                        ## Compare Correction Checkin to Start Checkin Times in working calendar
                        # Float to time convertion
                        check_in_correction_hrs = timedelta(hours=line.check_in_correction)
                        check_in_correction_hours = check_in_correction_hrs
                        check_in_correction_hr = str(check_in_correction_hours)
                        time_3 = check_in_correction_hr[-8:]
                        float_datetime_1 = datetime.strptime(time_3, '%H:%M:%S')

                        # spliting from check_in_correction float field
                        correction_checkin_hour = float_datetime_1.hour
                        correction_checkin_minute = float_datetime_1.minute

                        correction_checkin_date = line.date.day
                        correction_checkin_month = line.date.month
                        correction_checkin_year = line.date.year
                        concatenated_checkin = "%02d-%02d-%02d %02d:%02d:00" % (
                            correction_checkin_year, correction_checkin_month, correction_checkin_date,
                            correction_checkin_hour,
                            correction_checkin_minute)
                        # converting to timezone
                        correction_checkin_time = fields.Datetime.to_string(
                            pytz.timezone(self.env.context['tz']).localize(
                                fields.Datetime.from_string(concatenated_checkin),
                                is_dst=None).astimezone(pytz.utc))
                        correction_checkin_time = datetime.strptime(correction_checkin_time, '%Y-%m-%d %H:%M:%S')
                        if correction_checkin_time < working_calendar.start_checkin:
                            raise ValidationError("Check In time cannot be less than the specified Start CheckIn schedule. Please contact the Administrator!")
                    if line.hr_attendance_id and line.check_out_correction:
                        ## Compare Correction Checkout to End Checkout Times in working calendar
                        # Float to time convertion
                        check_out_correction_hrs = timedelta(hours=line.check_out_correction)
                        check_out_correction_hours = check_out_correction_hrs
                        check_out_correction_hr = str(check_out_correction_hours)
                        time_out_1 = check_out_correction_hr[-8:]
                        float_datetime_2 = datetime.strptime(time_out_1, '%H:%M:%S')

                        # spliting from check_out_correction float field
                        correction_checkout_hour = float_datetime_2.hour
                        correction_checkout_minute = float_datetime_2.minute

                        correction_checkout_date = line.date.day
                        correction_checkout_month = line.date.month
                        correction_checkout_year = line.date.year
                        concatenated_checkout = "%02d-%02d-%02d %02d:%02d:00" % (
                            correction_checkout_year, correction_checkout_month, correction_checkout_date,
                            correction_checkout_hour,
                            correction_checkout_minute)
                        # converting to timezone
                        correction_checkout_time = fields.Datetime.to_string(
                            pytz.timezone(self.env.context['tz']).localize(
                                fields.Datetime.from_string(concatenated_checkout),
                                is_dst=None).astimezone(pytz.utc))
                        correction_checkout_time = datetime.strptime(correction_checkout_time, '%Y-%m-%d %H:%M:%S')
                        if line.check_out_correction < line.check_in_correction:
                            correction_checkout_time = correction_checkout_time + relativedelta(days=1)
                        if correction_checkout_time > working_calendar.end_checkout:
                            raise ValidationError("Checkout time cannot be greater than the specified End Checkout schedule. Please contact the Administrator!")

            if setting:
                self.approver_mail()
                rec.write({'state': 'to_approve'})
                self.approver_wa_template()
                for line in rec.attendance_change_user_ids:
                    line.write({'approver_state': 'draft'})
            else:
                rec.write({'state': 'approved'})
            #Dont delete, validation warning for reason field
            # if rec.attendance_change_line_ids:
            #     for line in rec.attendance_change_line_ids:
            #         if line.hr_attendance_id and line.check_in_correction != 0.0 and not line.reason:
            #             raise ValidationError("Please fill the reason field.")
            #         elif line.hr_attendance_id and line.check_out_correction != 0.0 and not line.reason:
            #             raise ValidationError("Please fill the reason field")
            #         else:
            #             rec.write({'state': 'to_approve'})

    def action_attendance_change(self):
        for rec in self:
            if rec.attendance_change_line_ids:
                for line in rec.attendance_change_line_ids:
                    if line.hr_attendance_id and line.check_in_correction != 0.0:
                        # Float to time convertion
                        check_in_correction_hrs = timedelta(hours=line.check_in_correction)
                        check_in_correction_hours = check_in_correction_hrs
                        check_in_correction_hr = str(check_in_correction_hours)
                        time_3 = check_in_correction_hr[-8:]
                        float_datetime_1 = datetime.strptime(time_3, '%H:%M:%S')

                        # spliting from check_in_correction float field
                        correction_checkin_hour = float_datetime_1.hour
                        correction_checkin_minute = float_datetime_1.minute

                        # spliting from check_in from attendance datetime field
                        if line.check_in != 0.0:
                            original_checkin_date = line.hr_attendance_id.check_in.day
                            original_checkin_month = line.hr_attendance_id.check_in.month
                            original_checkin_year = line.hr_attendance_id.check_in.year
                            concatenated_checkin = "%02d-%02d-%02d %02d:%02d:00" % (
                                original_checkin_year, original_checkin_month, original_checkin_date,
                                correction_checkin_hour,
                                correction_checkin_minute)
                            # converting to timezone
                            update_checkin = fields.Datetime.to_string(
                                pytz.timezone(self.env.context['tz']).localize(
                                    fields.Datetime.from_string(concatenated_checkin),
                                    is_dst=None).astimezone(pytz.utc))

                            line.hr_attendance_id.update({
                                'check_in': update_checkin,
                                'hr_attendance_change_id': rec.id,
                            })
                        elif line.check_in == 0.0:
                            original_checkin_date = line.date.day
                            original_checkin_month = line.date.month
                            original_checkin_year = line.date.year
                            concatenated_checkin = "%02d-%02d-%02d %02d:%02d:00" % (
                                original_checkin_year, original_checkin_month, original_checkin_date,
                                correction_checkin_hour,
                                correction_checkin_minute)
                            # converting to timezone
                            update_checkin = fields.Datetime.to_string(
                                pytz.timezone(self.env.context['tz']).localize(
                                    fields.Datetime.from_string(concatenated_checkin),
                                    is_dst=None).astimezone(pytz.utc))

                            line.hr_attendance_id.update({
                                'check_in': update_checkin,
                                'hr_attendance_change_id': rec.id,
                            })
                    if line.hr_attendance_id and line.check_out_correction != 0.0:
                        # Float to time convertion
                        check_out_correction_hrs = timedelta(hours=line.check_out_correction)
                        check_out_correction_hours = check_out_correction_hrs
                        check_out_correction_hr = str(check_out_correction_hours)
                        time_out_1 = check_out_correction_hr[-8:]
                        float_datetime_2 = datetime.strptime(time_out_1, '%H:%M:%S')

                        # spliting from check_out_correction float field
                        correction_checkout_hour = float_datetime_2.hour
                        correction_checkout_minute = float_datetime_2.minute

                        # spliting from check_out from attendance datetime field
                        if line.check_out != 0.0:
                            original_checkout_date = line.hr_attendance_id.check_out.day
                            original_checkout_month = line.hr_attendance_id.check_out.month
                            original_checkout_year = line.hr_attendance_id.check_out.year
                            concatenated_checkout = "%02d-%02d-%02d %02d:%02d:00" % (
                                original_checkout_year, original_checkout_month, original_checkout_date,
                                correction_checkout_hour,
                                correction_checkout_minute)
                            # converting to timezone
                            update_checkout = fields.Datetime.to_string(
                                pytz.timezone(self.env.context['tz']).localize(
                                    fields.Datetime.from_string(concatenated_checkout),
                                    is_dst=None).astimezone(pytz.utc))
                            update_checkout = datetime.strptime(update_checkout, '%Y-%m-%d %H:%M:%S')
                            if line.check_out_correction < line.check_in_correction:
                                update_checkout = update_checkout + relativedelta(days=1)
                            line.hr_attendance_id.update({
                                'check_out': update_checkout,
                                'hr_attendance_change_id': rec.id,
                            })
                        elif line.check_out == 0.0:
                            original_checkout_date = line.date.day
                            original_checkout_month = line.date.month
                            original_checkout_year = line.date.year
                            concatenated_checkout = "%02d-%02d-%02d %02d:%02d:00" % (
                                original_checkout_year, original_checkout_month, original_checkout_date,
                                correction_checkout_hour,
                                correction_checkout_minute)
                            # converting to timezone
                            update_checkout = fields.Datetime.to_string(
                                pytz.timezone(self.env.context['tz']).localize(
                                    fields.Datetime.from_string(concatenated_checkout),
                                    is_dst=None).astimezone(pytz.utc))
                            update_checkout = datetime.strptime(update_checkout, '%Y-%m-%d %H:%M:%S')
                            if line.check_out_correction < line.check_in_correction:
                                update_checkout = update_checkout + relativedelta(days=1)
                            line.hr_attendance_id.update({
                                'check_out': update_checkout,
                                'hr_attendance_change_id': rec.id,
                            })

                    if line.hr_attendance_id and line.checkin_status_correction:
                        line.hr_attendance_id.update({
                            'hr_attendance_change_id': rec.id,
                            'checkin_status_correction': line.checkin_status_correction,
                        })
                        if line.hr_attendance_id.attendance_status == 'absent':
                            line.hr_attendance_id.update({
                                'attendance_status': 'present',
                            })
                        else:
                            line.hr_attendance_id.attendance_status = line.hr_attendance_id.attendance_status

                    if line.hr_attendance_id and line.checkout_status_correction:
                        line.hr_attendance_id.update({
                            'hr_attendance_change_id': rec.id,
                            'checkout_status_correction': line.checkout_status_correction,
                        })
                        if line.hr_attendance_id.attendance_status == 'absent':
                            line.hr_attendance_id.update({
                                'attendance_status': 'present',
                            })
                        else:
                            line.hr_attendance_id.attendance_status = line.hr_attendance_id.attendance_status
                    if line.hr_attendance_id and line.attendance_status_correction:
                        line.hr_attendance_id.update({
                            'hr_attendance_change_id': rec.id,
                            'attendance_status': line.attendance_status_correction,
                        })

    def action_approve(self):
        sequence_matrix = [data.name for data in self.attendance_change_user_ids]
        sequence_approval = [data.name for data in self.attendance_change_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.attendance_change_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        for record in self:
            current_user = self.env.uid
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_attendance_extend.attendance_type_approval')
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            if setting == 'employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.attendance_change_user_ids:
                            for hie_user in user.user_ids:
                                if current_user == hie_user.id:
                                    user.is_approve = True
                                    user.timestamp = fields.Datetime.now()
                                    user.approver_state = 'approved'
                                    string_approval = []
                                    if user.approval_status:
                                        string_approval.append(f"{self.env.user.name}:Approved")
                                        user.approval_status = "\n".join(string_approval)
                                        string_timestammp = [user.approved_time]
                                        string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                        user.approved_time = "\n".join(string_timestammp)
                                        if record.feedback_parent:
                                            feedback_list = [user.feedback,
                                                             f"{self.env.user.name}:{record.feedback_parent}"]
                                            final_feedback = "\n".join(feedback_list)
                                            user.feedback = f"{final_feedback}"
                                        elif user.feedback and not record.feedback_parent:
                                            user.feedback = user.feedback
                                        else:
                                            user.feedback = ""
                                    else:
                                        user.approval_status = f"{self.env.user.name}:Approved"
                                        user.approved_time = f"{self.env.user.name}:{dateformat}"
                                        if record.feedback_parent:
                                            user.feedback = f"{self.env.user.name}:{record.feedback_parent}"
                                        else:
                                            user.feedback = ""
                                    record.approved_user_ids = [(4, current_user)]
                        matrix_line = sorted(record.attendance_change_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            self.approved_mail()
                            record.write({'state': 'approved'})
                            record.action_attendance_change()
                            self.approved_wa_template()
                        else:
                            self.approver_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has been approved the Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
                                self.approver_wa_template()
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved'
                    ))
            elif setting == 'approval_matrix':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for line in record.attendance_change_user_ids:
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
                                            if record.feedback_parent:
                                                feedback_list = [line.feedback,
                                                                 f"{self.env.user.name}:{record.feedback_parent}"]
                                                final_feedback = "\n".join(feedback_list)
                                                line.feedback = f"{final_feedback}"
                                            elif line.feedback and not record.feedback_parent:
                                                line.feedback = line.feedback
                                            else:
                                                line.feedback = ""
                                        else:
                                            line.approval_status = f"{self.env.user.name}:Approved"
                                            line.approved_time = f"{self.env.user.name}:{dateformat}"
                                            if record.feedback_parent:
                                                line.feedback = f"{self.env.user.name}:{record.feedback_parent}"
                                            else:
                                                line.feedback = ""
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
                                            if record.feedback_parent:
                                                feedback_list = [line.feedback,
                                                                 f"{self.env.user.name}:{record.feedback_parent}"]
                                                final_feedback = "\n".join(feedback_list)
                                                line.feedback = f"{final_feedback}"
                                            elif line.feedback and not record.feedback_parent:
                                                line.feedback = line.feedback
                                            else:
                                                line.feedback = ""
                                        else:
                                            line.approval_status = f"{self.env.user.name}:Approved"
                                            line.approved_time = f"{self.env.user.name}:{dateformat}"
                                            if record.feedback_parent:
                                                line.feedback = f"{self.env.user.name}:{record.feedback_parent}"
                                            else:
                                                line.feedback = ""
                                    line.approved_employee_ids = [(4, current_user)]

                        matrix_line = sorted(record.attendance_change_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            self.approved_mail()
                            record.write({'state': 'approved'})
                            record.action_attendance_change()
                            self.approved_wa_template()
                        else:
                            self.approver_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
                                self.approver_wa_template()
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved!'
                    ))
            else:
                raise ValidationError(_(
                    'Already approved!'
                ))

    def action_refuse(self):
        for record in self:
            for user in record.attendance_change_user_ids:
                for check_user in user.user_ids:
                    now = datetime.now(timezone(self.env.user.tz))
                    dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
                    if self.env.uid == check_user.id:
                        user.timestamp = fields.Datetime.now()
                        user.approver_state = 'refuse'
                        string_approval = []
                        string_approval.append(user.approval_status)
                        if user.approval_status:
                            string_approval.append(f"{self.env.user.name}:Refused")
                            user.approval_status = "\n".join(string_approval)
                            string_timestammp = [user.approved_time]
                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                            user.approved_time = "\n".join(string_timestammp)
                        else:
                            user.approval_status = f"{self.env.user.name}:Refused"
                            user.approved_time = f"{self.env.user.name}:{dateformat}"
            self.reject_mail()
            record.approved_user = self.env.user.name + ' ' + 'has been Rejected!'
            record.write({'state': 'refused'})
            self.rejected_wa_template()

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.change.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':True},
            'target': 'new',
        }

    def wizard_refuse(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.change.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':False, 'default_state':'rejected'},
            'target': 'new',
        }
    # Dont delete, validation warning for reason field
    # @api.constrains('attendance_change_line_ids')
    # def _check_reason(self):
    #     for rec in self:
    #         if rec.attendance_change_line_ids:
    #             for line in rec.attendance_change_line_ids:
    #                 if line.hr_attendance_id and line.check_in_correction != 0.0 and not line.reason :
    #                     raise ValidationError("Please fill the reason field.")
    #                 elif line.hr_attendance_id and line.check_out_correction != 0.0 and not line.reason:
    #                     raise ValidationError("Please fill the reason field")
    @api.constrains('request_date_from')
    def _check_request_date_from(self):
        for rec in self:
            if rec.request_date_from and rec.request_date_from  >= date.today():
                raise ValidationError("Cannot changes attendance data on a date that has not passed")

class HrAttendanceChangeLine(models.Model):
    _name = 'hr.attendance.change.line'

    hr_attendance_change_id = fields.Many2one('hr.attendance.change', string="Attendance Line")
    date = fields.Date('Date')
    resource_calendar_id = fields.Many2one('resource.calendar', 'Working Schedule', compute='_compute_resource_calendar')
    check_in = fields.Float(string="Original Check In")
    check_out = fields.Float(string="Original Check Out")
    checkin_status = fields.Selection(
        [('early', 'Early'), ('ontime', 'Ontime'), ('late', 'Late'), ('no_checking', 'No Checkin')],
        string='Checkin Status' )
    checkout_status = fields.Selection(
        [('early', 'Early'), ('ontime', 'Ontime'), ('late', 'Late'), ('no_checkout', 'No Checkout')],
        string='Checkout Status')
    attendance_status = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('leave', 'Leave'),
                                          ('travel', 'Travel')],
                                         string='Original Attendance Status')
    check_in_correction = fields.Float(string="Check In Correction")
    check_out_correction = fields.Float(string="Check Out Correction")
    checkin_status_correction = fields.Selection(
        [('early', 'Early'), ('ontime', 'Ontime'), ('late', 'Late'), ('no_checking', 'No Checkin')],
        string='Checkin Status Correction')
    checkout_status_correction = fields.Selection(
        [('early', 'Early'), ('ontime', 'Ontime'), ('late', 'Late'), ('no_checkout', 'No Checkout')],
        string='Checkout Status Correction')
    attendance_status_correction = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('leave', 'Leave'),
                                          ('travel', 'Travel')],
                                         string='Attendance Status Correction')
    reason = fields.Text(string='Reason')
    hr_attendance_id = fields.Many2one('hr.attendance', string="Attendance")

    @api.depends('date','hr_attendance_change_id','hr_attendance_change_id.employee_id')
    def _compute_resource_calendar(self):
        for rec in self:
            schedule = self.env['employee.working.schedule.calendar'].search(
                [('employee_id', '=', rec.hr_attendance_change_id.employee_id.id), ('date_start', '=', rec.date)], limit=1)
            if schedule:
                if schedule.working_hours:
                    rec.resource_calendar_id = schedule.working_hours
                else:
                    if rec.hr_attendance_change_id.employee_id.resource_calendar_id:
                        rec.resource_calendar_id = rec.hr_attendance_change_id.employee_id.resource_calendar_id.id
                    else:
                        rec.resource_calendar_id = False
            else:
                if rec.hr_attendance_change_id.employee_id.resource_calendar_id:
                    rec.resource_calendar_id = rec.hr_attendance_change_id.employee_id.resource_calendar_id.id
                else:
                    rec.resource_calendar_id = False

class AttendanceChangeApproverUser(models.Model):
    _name = 'attendance.change.approver.user'

    attendance_change_approver_id = fields.Many2one('hr.attendance.change', string="Advance Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'attendance_change_app_emp_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'att_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='attendance_change_approver_id.state')

    @api.depends('attendance_change_approver_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.attendance_change_approver_id.attendance_change_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.attendance_change_approver_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.attendance_change_approver_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids