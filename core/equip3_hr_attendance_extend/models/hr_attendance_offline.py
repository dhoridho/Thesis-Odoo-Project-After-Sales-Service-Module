# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import format_datetime
import pytz
from dateutil.relativedelta import relativedelta
import requests
from odoo.exceptions import UserError, ValidationError

class HrAttendanceOffline(models.Model):
    _name = 'hr.attendance.offline'
    _description = 'Hr Attendance Offline'
    _order = 'start_working_date desc'

    def _get_attendance_status(self):
        return self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.attendance_status') or ''

    employee_id = fields.Many2one('hr.employee', string='Employee')
    employee_id_image = fields.Image(string="Image employee", related='employee_id.image_1920')
    sequence_code = fields.Char(string='Employee ID', related="employee_id.sequence_code",
                                readonly=True, store=True)
    department_id = fields.Many2one('hr.department', string='Department', related="employee_id.department_id",
                                    readonly=True, store=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', string='Job Positions', store=True)
    manager_id = fields.Many2one('hr.employee', string='Manager', related='employee_id.parent_id', store=True)
    working_schedule_id = fields.Many2one('resource.calendar', string='Working Schedule', compute='_compute_working_schedule')
    active_location_ids = fields.Many2many('res.partner', string='Active Location', compute='_compute_active_location')
    start_working_date = fields.Date(string='Working Date')
    calendar_id = fields.Many2one('employee.working.schedule.calendar', string='Calendar', compute='_compute_calendar', compute_sudo=True)
    hour_from = fields.Float(string='Work From', compute='_compute_calendar', store=True)
    hour_to = fields.Float(string='Work To', compute='_compute_calendar', store=True)
    tolerance_late = fields.Float(string='Tolerance for Late',
                                  compute='_compute_calendar', store=True)
    attendance_status = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('leave', 'Leave'),
                                          ('travel', 'Travel')],
                                         string='Attendance Status', default=_get_attendance_status)
    check_in = fields.Datetime(string="Check In")
    checkin_status = fields.Selection(
        [('early', 'Early'), ('ontime', 'Ontime'), ('late', 'Late'), ('no_checking', 'No Checkin')],
        string='Checkin Status', compute='_compute_checkin_status', store=True)
    check_out = fields.Datetime(string="Check Out")
    checkout_status = fields.Selection(
        [('early', 'Early'), ('ontime', 'Ontime'), ('late', 'Late'), ('no_checkout', 'No Checkout')],
        string='Checkout Status', compute='_compute_checkout_status', store=True)
    minimum_hours = fields.Float(string='Minimum Hours', compute='_compute_minimum_work_hrs', readonly=True, store=True)
    check_in_diff = fields.Float(string='Check In Difference', compute='_compute_checkin_diff',
                                 readonly=True, store=True)
    check_out_diff = fields.Float(string='Check Out Difference', compute='_compute_checkout_diff',
                                  readonly=True, store=True)
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True, readonly=True)
    count_status = fields.Selection(
        [('not_fulfilled', 'Not Fulfilled'), ('fulfilled', 'Fulfilled')], 
        string='Count Status', compute='_compute_count_status', store=True)
    check_in_latitude = fields.Float(
        "Check-in Latitude", digits="Location", readonly=True
    )
    check_in_longitude = fields.Float(
        "Check-in Longitude", digits="Location", readonly=True
    )
    check_out_latitude = fields.Float(
        "Check-out Latitude", digits="Location", readonly=True
    )
    check_out_longitude = fields.Float(
        "Check-out Longitude", digits="Location", readonly=True
    )
    check_in_address = fields.Char('Check In Address', compute="_get_checkin_address", store=True, readonly=True)
    check_out_address = fields.Char('Check Out Address', compute="_get_checkout_address", store=True, readonly=True)
    webcam_check_in = fields.Binary(string="Webcam snapshot check in", readonly=True)
    webcam_check_out = fields.Binary(string="Webcam snapshot check out", readonly=True)
    check_in_face_distance = fields.Float(string="Check-In Face Distance")
    check_out_face_distance = fields.Float(string="Check-Out Face Distance")
    state = fields.Selection([("to_approve", "To Approve"),
                              ("approved", "Approved"),
                              ("rejected", "Rejected")
                              ], string='Status', default="to_approve")
    approvers_ids = fields.Many2many('res.users', 'approver_users_attendance_offline_rel', string='Approvers')
    approved_user_ids = fields.Many2many('res.users', string='Approved User')
    approver_user_ids = fields.One2many('hr.attendance.offline.approver.user', 'attendance_offline_id', string='Approver')
    is_approver = fields.Boolean(string="Is Approver", compute="_compute_is_approver")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrAttendanceOffline, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrAttendanceOffline, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def create(self, vals):
        res = super(HrAttendanceOffline, self).create(vals)
        if res.employee_id:
            self.approval_by_matrix(res)
        return res

    def name_get(self):
        result = []
        for attendance in self:
            if not attendance.check_out:
                result.append((attendance.id, _("%(empl_name)s from %(check_in)s") % {
                    'empl_name': attendance.employee_id.name,
                    'check_in': format_datetime(self.env, attendance.check_in, dt_format=False),
                }))
            else:
                result.append((attendance.id, _("%(empl_name)s from %(check_in)s to %(check_out)s") % {
                    'empl_name': attendance.employee_id.name,
                    'check_in': format_datetime(self.env, attendance.check_in, dt_format=False),
                    'check_out': format_datetime(self.env, attendance.check_out, dt_format=False),
                }))
        return result
    
    def custom_menu(self):
        if self.env.user.has_group(
                'hr_attendance.group_hr_attendance_user') and not self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_attendance_hr_manager'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Attendances Offline',
                    'res_model': 'hr.attendance.offline',
                    'target': 'current',
                    'view_mode': 'tree,form',
                    'domain': [('employee_id', 'in', employee_ids)],
                    'help': """<p class="o_view_nocontent_smiling_face">
                        No attendances offline records found
                    </p>"""

                }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Attendances Offline',
                'res_model': 'hr.attendance.offline',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [],
                'help': """<p class="o_view_nocontent_smiling_face">
                    No attendances offline records found
                </p>""",
            }
    
    @api.onchange('employee_id')
    def onchange_employee(self):
        for record in self:
            if record.employee_id:
                if record.approver_user_ids:
                    remove = []
                    for line in record.approver_user_ids:
                        remove.append((2, line.id))
                    record.approver_user_ids = remove
                self.approval_by_matrix(record)

    def get_manager_hierarchy(self, attendance, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(attendance, employee_manager['parent_id'], data, manager_ids, seq, level)
                break
        return manager_ids
    
    def approval_by_matrix(self, record):
        approval_matrix = self.env['hr.attendance.offline.approval.matrix'].search([('apply_to', '=', 'by_employee')])
        matrix = approval_matrix.filtered(lambda line: record.employee_id.id in line.employee_ids.ids)
        app_list = []
        if matrix:
            data_approvers = []
            for line in matrix[0].approval_matrix_ids:
                if line.approver_types == "specific_approver":
                    data_approvers.append((0, 0, {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                  'approver_ids': [(6, 0, line.approver_ids.ids)]}))
                    for approvers in line.approver_ids:
                        app_list.append(approvers.id)
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data = 0
                    approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'approver_ids': [(4, approver)]}))
                        app_list.append(approver)
            record.approvers_ids = app_list
            record.approver_user_ids = data_approvers
        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.attendance.offline.approval.matrix'].search(
                [('apply_to', '=', 'by_job_position')])
            matrix = approval_matrix.filtered(lambda line: record.employee_id.job_id.id in line.job_ids.ids)
            if matrix:
                for line in matrix[0].approval_matrix_ids:
                    if line.approver_types == "specific_approver":
                        data_approvers.append((0, 0, {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                      'approver_ids': [(6, 0, line.approver_ids.ids)]}))
                        for approvers in line.approver_ids:
                            app_list.append(approvers.id)
                    elif line.approver_types == "by_hierarchy":
                        manager_ids = []
                        seq = 1
                        data = 0
                        approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'approver_ids': [(4, approver)]}))
                            app_list.append(approver)
                record.approvers_ids = app_list
                record.approver_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.attendance.offline.approval.matrix'].search(
                    [('apply_to', '=', 'by_department')])
                matrix = approval_matrix.filtered(lambda line: record.employee_id.department_id.id in line.department_ids.ids)
                if matrix:
                    for line in matrix[0].approval_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0, 0,
                                                   {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                    'approver_ids': [(6, 0, line.approver_ids.ids)]}))
                            for approvers in line.approver_ids:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'approver_ids': [(4, approver)]}))
                                app_list.append(approver)
                    record.approvers_ids = app_list
                    record.approver_user_ids = data_approvers
    
    def _compute_is_approver(self):
        for rec in self:
            if rec.approvers_ids:
                current_user = rec.env.user
                matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(rec.approver_user_ids)
                if app < a:
                    for line in rec.approver_user_ids[app]:
                        if current_user in line.approver_ids:
                            rec.is_approver = True
                        else:
                            rec.is_approver = False
                else:
                    rec.is_approver = False
            else:
                rec.is_approver = False

    @api.depends('employee_id')
    def _compute_working_schedule(self):
        for rec in self:
            contract = self.env['hr.contract'].search([('employee_id', '=', rec.employee_id.id),], order='id desc', limit=1)
            if contract:
                rec.working_schedule_id = contract.resource_calendar_id
            else:
                rec.working_schedule_id = False
    
    @api.depends('employee_id')
    def _compute_active_location(self):
        for rec in self:
            if rec.employee_id:
                rec.active_location_ids = rec.employee_id.active_location
            else:
                rec.active_location_ids = False
    
    @api.onchange('check_in')
    def onchange_check_in(self):
        for rec in self:
            if rec.check_in:
                employee_tz = rec.employee_id.tz or 'UTC'
                local = pytz.timezone(employee_tz)
                check_in = pytz.UTC.localize(rec.check_in).astimezone(local)
                convert_to_date = fields.Datetime.from_string(check_in.date()).strftime('%Y-%m-%d')
                rec.start_working_date = convert_to_date

    @api.depends('start_working_date')
    def _compute_calendar(self):
        for rec in self:
            schedule = self.env['employee.working.schedule.calendar'].search(
                [('employee_id', '=', rec.employee_id.id), ('date_start', '=', rec.start_working_date)], limit=1)
            if schedule:
                rec.calendar_id = schedule.id
                rec.hour_from = schedule.hour_from
                rec.hour_to = schedule.hour_to
                rec.tolerance_late = schedule.tolerance_late
            else:
                rec.calendar_id = False
                rec.hour_from = 0
                rec.hour_to = 0
                rec.tolerance_late = 0

    @api.depends('check_in','calendar_id')
    def _compute_checkin_status(self):
        for attendance in self:
            if attendance.calendar_id:
                checkin_ontime = attendance.calendar_id.checkin + relativedelta(
                    hours=attendance.calendar_id.tolerance_late)
                if not attendance.check_in:  # no check in
                    attendance.checkin_status = 'no_checking'
                elif attendance.check_in < attendance.calendar_id.checkin:  # Early
                    attendance.checkin_status = 'early'
                elif attendance.check_in > checkin_ontime:  # late
                    attendance.checkin_status = 'late'
                elif attendance.check_in >= attendance.calendar_id.checkin <= checkin_ontime:  # ontime
                    attendance.checkin_status = 'ontime'
            else:
                attendance.checkin_status = ''
    
    @api.depends('check_out','calendar_id','worked_hours')
    def _compute_checkout_status(self):
        for attendance in self:
            if attendance.calendar_id:
                if not attendance.check_out:
                    attendance.checkout_status = 'no_checkout'
                elif attendance.worked_hours < attendance.calendar_id.minimum_hours:  # Early
                    attendance.checkout_status = 'early'
                elif attendance.worked_hours > attendance.calendar_id.minimum_hours:  # late
                    attendance.checkout_status = 'late'
                elif attendance.worked_hours == attendance.calendar_id.minimum_hours:  # ontime
                    attendance.checkout_status = 'ontime'
            else:
                attendance.checkout_status = ''
    
    @api.depends('calendar_id')
    def _compute_minimum_work_hrs(self):
        for attendance in self:
            if attendance.calendar_id:
                attendance.minimum_hours = attendance.calendar_id.minimum_hours
            else:
                attendance.minimum_hours = 0

    @api.depends('check_in','calendar_id')
    def _compute_checkin_diff(self):
        for attendance in self:
            if attendance.calendar_id:
                checkin_ontime = attendance.calendar_id.checkin + relativedelta(
                    hours=attendance.calendar_id.tolerance_late)
                if not attendance.check_in:
                    attendance.check_in_diff = 0
                elif attendance.check_in < attendance.calendar_id.checkin:  # Early
                    attendance.check_in_diff = (attendance.check_in - checkin_ontime).total_seconds() / 3600
                elif attendance.check_in > checkin_ontime:  # late
                    attendance.check_in_diff = (attendance.check_in - checkin_ontime).total_seconds() / 3600
                else:
                    attendance.check_in_diff = 0
    
    @api.depends('check_out','calendar_id')
    def _compute_checkout_diff(self):
        for attendance in self:
            if attendance.calendar_id:
                checkout_ontime = attendance.calendar_id.checkout + relativedelta(
                    hours=attendance.calendar_id.tolerance_late)
                if not attendance.check_out:
                    attendance.check_out_diff = 0
                elif attendance.check_out < attendance.calendar_id.checkout:  # Early
                    attendance.check_out_diff = (attendance.calendar_id.checkout - attendance.check_out).total_seconds() / 3600
                elif attendance.check_out > checkout_ontime:  # late
                    attendance.check_out_diff = (attendance.calendar_id.checkout - attendance.check_out).total_seconds() / 3600
                else:
                    attendance.check_out_diff = 0
    
    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in:
                delta = attendance.check_out - attendance.check_in
                attendance.worked_hours = delta.total_seconds() / 3600.0
            else:
                attendance.worked_hours = False

    @api.depends('minimum_hours', 'worked_hours', 'attendance_status')
    def _compute_count_status(self):
        for attendance in self:
            if attendance.worked_hours >= attendance.minimum_hours and not attendance.attendance_status == 'absent':
                attendance.count_status = "fulfilled"
            else:
                attendance.count_status = "not_fulfilled"
            
    @api.depends('check_in_latitude','check_in_longitude')
    def _get_checkin_address(self):
        for attendance in self:
            self.env['ir.config_parameter'].set_param('gmaps_reverse_geocoding_token',
                                                      'AIzaSyDVSmaYy-QzDU0yANwsZv2lURQGMN3vnMU')
            api_key = self.env['ir.config_parameter'].get_param('gmaps_reverse_geocoding_token')
            if api_key:
                if attendance.check_in_latitude != 0 and attendance.check_in_longitude != 0:
                    response = requests.get(
                        'https://maps.googleapis.com/maps/api/geocode/json?latlng={},{}&key={}'.format(
                            attendance.check_in_latitude, attendance.check_in_longitude, api_key))
                    if response.json().get('status') == 'OK':
                        attendance.update({
                            'check_in_address': response.json().get('results')[0].get('formatted_address'),
                        })
                else:
                    attendance.check_in_address = '-'
            else:
                raise Warning(_('Google Reverse GeoCoding Token Not found!!'))

    @api.depends('check_out_latitude','check_out_longitude')
    def _get_checkout_address(self):
        for attendance in self:
            self.env['ir.config_parameter'].set_param('gmaps_reverse_geocoding_token',
                                                      'AIzaSyDVSmaYy-QzDU0yANwsZv2lURQGMN3vnMU')
            api_key = self.env['ir.config_parameter'].get_param('gmaps_reverse_geocoding_token')
            if api_key:
                if attendance.check_out_latitude != 0 and attendance.check_out_longitude != 0:
                    response = requests.get(
                        'https://maps.googleapis.com/maps/api/geocode/json?latlng={},{}&key={}'.format(
                            attendance.check_out_latitude, attendance.check_out_longitude, api_key))
                    if response.json().get('status') == 'OK':
                        attendance.update({
                            'check_out_address': response.json().get('results')[0].get('formatted_address'),
                        })
                else:
                    attendance.check_out_address = '-'
            else:
                raise Warning(_('Google Reverse GeoCoding Token Not found!!'))
    
    def open_map_check_in(self):
        self.ensure_one()
        map_website = "https://maps.google.com/maps?z=17&t=m&q={LATITUDE},{LONGITUDE}"
        if (hasattr(self, 'check_in_latitude') and
                self.check_in_latitude and self.check_in_longitude):
            url = self._prepare_url(
                map_website, {
                    '{LATITUDE}': self.check_in_latitude,
                    '{LONGITUDE}': self.check_in_longitude})
        else:
            raise UserError(
                _("Missing parameter 'Latitude / Longitude' "
                  "for Check-in"))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def open_map_check_out(self):
        self.ensure_one()
        map_website = "https://maps.google.com/maps?z=17&t=m&q={LATITUDE},{LONGITUDE}"
        if (hasattr(self, 'check_out_latitude') and
                self.check_out_latitude and self.check_out_longitude):
            url = self._prepare_url(
                map_website, {
                    '{LATITUDE}': self.check_out_latitude,
                    '{LONGITUDE}': self.check_out_longitude})
        else:
            raise UserError(
                _("Missing parameter 'Latitude / Longitude' "
                  "for Check-out"))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
    
    def wizard_approve(self):
        self.approver_user_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.offline.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'default_attendance_offline_id':self.id,'default_state':'approved'},
            'target': 'new',
        }

    def wizard_reject(self):
        self.approver_user_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.offline.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'default_attendance_offline_id':self.id,'default_state':'rejected'},
            'target': 'new',
        }
    
    def action_update_attendance(self):
        for rec in self:
            attendance_id = self.env['hr.attendance'].sudo().search([('employee_id', '=', rec.employee_id.id),('start_working_date', '=', rec.start_working_date),('active','=',True)], limit=1)
            if attendance_id:
                attendance_id.write({
                    'check_in': False,
                    'check_out': False,
                })
                attendance_id.update({
                    'check_in': rec.check_in,
                    'check_out': rec.check_out,
                    'attendance_status': rec.attendance_status,
                    'check_in_latitude': rec.check_in_latitude,
                    'check_in_longitude': rec.check_in_longitude,
                    'check_out_latitude': rec.check_out_latitude,
                    'check_out_longitude': rec.check_out_longitude,
                    'check_in_address': rec.check_in_address,
                    'check_out_address': rec.check_out_address,
                    'webcam_check_in': rec.webcam_check_in,
                    'webcam_check_out': rec.webcam_check_out,
                })
            else:
                self.env['hr.attendance'].sudo().create({
                    'employee_id': rec.employee_id.id,
                    'start_working_date': rec.start_working_date,
                    'check_in': rec.check_in,
                    'check_out': rec.check_out,
                    'attendance_status': rec.attendance_status,
                    'check_in_latitude': rec.check_in_latitude,
                    'check_in_longitude': rec.check_in_longitude,
                    'check_out_latitude': rec.check_out_latitude,
                    'check_out_longitude': rec.check_out_longitude,
                    'check_in_address': rec.check_in_address,
                    'check_out_address': rec.check_out_address,
                    'webcam_check_in': rec.webcam_check_in,
                    'webcam_check_out': rec.webcam_check_out,
                })
    
    @api.returns('self', lambda value: value.id)
    def copy(self):
        raise UserError(_('You cannot duplicate an attendance.'))

class HrAttendanceOfflineApproverUser(models.Model):
    _name = 'hr.attendance.offline.approver.user'

    attendance_offline_id = fields.Many2one('hr.attendance.offline', string="Attendance Offline")
    sequence = fields.Integer('Sequence', compute="fetch_sl_no")
    approver_ids = fields.Many2many('res.users', string="Approvers")
    approved_user_ids = fields.Many2many('res.users', 'att_offline_matrix_approved_users_rel', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    approval_status = fields.Text(string="Approval Status")
    timestamp = fields.Text('Timestamp')
    feedback = fields.Text('Feedback')
    is_approve = fields.Boolean(string="Is Approve", default=False)
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='draft', string="State")
    #parent status
    state = fields.Selection(string='Parent Status', related='attendance_offline_id.state')

    @api.depends('attendance_offline_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.attendance_offline_id.approver_user_ids:
            sl = sl + 1
            line.sequence = sl
        self.update_minimum_app()
    
    def update_minimum_app(self):
        for rec in self:
            if len(rec.approver_ids) < rec.minimum_approver:
                rec.minimum_approver = len(rec.approver_ids)
    
    def update_approver_state(self):
        for rec in self:
            if rec.attendance_offline_id.state == 'to_approve':
                if not rec.approved_user_ids:
                    rec.approver_state = 'draft'
                elif rec.approved_user_ids and rec.minimum_approver == len(rec.approved_user_ids):
                    rec.approver_state = 'approved'
                else:
                    rec.approver_state = 'pending'
            if rec.attendance_offline_id.state == 'rejected':
                rec.approver_state = 'refuse'