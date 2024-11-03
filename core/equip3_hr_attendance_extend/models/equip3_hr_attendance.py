# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from odoo import models, fields, api, _
import datetime
from datetime import date, datetime, timedelta
import pytz
import requests
from odoo.exceptions import UserError
import logging
from dateutil.relativedelta import relativedelta
from lxml import etree

logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError
import requests
from odoo.tools.misc import split_every
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
headers = {'content-type': 'application/json'}

class HrAttendance(models.Model):
    _inherit = "hr.attendance"
    _order = 'start_working_date desc'

    def _get_attendance_status(self):
        return self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.attendance_status') or ''

    active = fields.Boolean(default=True)
    is_created = fields.Boolean('Created', default=False)
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=False)
    sequence_code = fields.Char(string='Employee ID', related="employee_id.sequence_code",
                                readonly=True, store=True)
    department_id = fields.Many2one('hr.department', string='Department', related="employee_id.department_id",
                                    readonly=True, store=True)
    attendance_status = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('leave', 'Leave'),
                                          ('travel', 'Travel')],
                                         string='Attendance Status', default=_get_attendance_status)
    checkin_status = fields.Selection(
        [('early', 'Early'), ('ontime', 'Ontime'), ('late', 'Late'), ('no_checking', 'No Checkin')],
        string='Checkin Status', compute='_compute_worked_status', store=True)
    checkout_status = fields.Selection(
        [('early', 'Early'), ('ontime', 'Ontime'), ('late', 'Late'), ('no_checkout', 'No Checkout')],
        string='Checkout Status', compute='_compute_worked_status', store=True)
    minimum_hours = fields.Float(string='Minimum Hours', compute='_compute_minimum_work_hrs', readonly=True, store=True)
    check_in_diff = fields.Float(string='Check In Difference', compute='_compute_worked_status',
                                 readonly=True, store=True)
    check_out_diff = fields.Float(string='Check Out Difference', compute='_compute_worked_status',
                                  readonly=True, store=True)
    early_check_in_diff = fields.Float(string='Early Check In Diff', compute='_compute_worked_status',
                                 readonly=True, store=True)
    early_check_out_diff = fields.Float(string='Early Check Out Diff', compute='_compute_worked_status',
                                 readonly=True, store=True)
    late_check_out_diff = fields.Float(string='Late Check Out Diff', compute='_compute_worked_status',
                                 readonly=True, store=True)
    hr_attendance_change_id = fields.Many2one('hr.attendance.change', string='Attendance Change', readonly=True)
    check_in_address = fields.Char('Check In Address', compute="_get_address", store=True, readonly=True)
    check_out_address = fields.Char('Check Out Address', compute="_get_address", store=True, readonly=True)
    calendar_id = fields.Many2one('employee.working.schedule.calendar', string='Calendar', compute='_compute_calendar', compute_sudo=True)
    leave_id = fields.Many2one('hr.leave', string='Leave')
    start_working_times = fields.Datetime(string='Start Working Times')
    start_working_date = fields.Date(string='Working Date')
    hour_from = fields.Float(string='Work From', compute='_compute_calendar', store=True)
    hour_to = fields.Float(string='Work To', compute='_compute_calendar', store=True)
    tolerance_late = fields.Float(string='Tolerance for Late',
                                  compute='_compute_calendar', store=True)
    attendance_formula_id = fields.Many2one('hr.attendance.formula', string='Attendance Formula',
                                          compute='_compute_calendar', store=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', string='Job Positions', store=True)
    active_location_id = fields.Many2many('res.partner', string='Active Location')
    date_localization = fields.Date('Date Localization', related="employee_id.user_id.partner_id.date_localization",
                                    store=True)
    partner_latitude = fields.Float(string='Partner Latitude',
                                    related="employee_id.user_id.partner_id.partner_latitude", store=True)
    partner_longitude = fields.Float(string='Partner Longitude',
                                     related="employee_id.user_id.partner_id.partner_longitude", store=True)
    is_holiday = fields.Boolean(string='Is Holiday', default=False)
    holiday_remark = fields.Char(string='Holiday Remark')
    checkin_status_correction = fields.Selection(
        [('early', 'Early'), ('ontime', 'Ontime'), ('late', 'Late'), ('no_checking', 'No Checkin')],
        string='Checkin Status Correction')
    checkout_status_correction = fields.Selection(
        [('early', 'Early'), ('ontime', 'Ontime'), ('late', 'Late'), ('no_checkout', 'No Checkout')],
        string='Checkout Status Correction')
    working_schedule_id = fields.Many2one('resource.calendar', string='Working Schedule', compute='_compute_working_schedule')
    is_absent = fields.Boolean('is Absent', default=False)
    is_absent_email_sent = fields.Boolean('is Absent Email Sent', default=False)
    manager_id = fields.Many2one('hr.employee', string='Manager', related='employee_id.parent_id', store=True)
    # import Logic
    is_imported = fields.Boolean('Is Imported')
    count_status = fields.Selection(
        [('not_fulfilled', 'Not Fulfilled'), ('fulfilled', 'Fulfilled')], 
        string='Count Status', compute='_compute_count_status', store=True)
    leave_type = fields.Many2one("hr.leave.type", string="Leave Type")
    check_out = fields.Datetime()
    employee_id = fields.Many2one('hr.employee')
    date_server_check_in = fields.Datetime(string="Date Server Check In", compute="_compute_date_server_checkin", store=True)
    date_server_check_out = fields.Datetime(string="Date Server Check Out", compute="_compute_date_server_checkout", store=True)
    check_in_reason_categ = fields.Many2one('hr.attendance.reason.categ')
    check_out_reason_categ = fields.Many2one('hr.attendance.reason.categ')
    check_in_notes = fields.Text()
    check_out_notes = fields.Text()
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrAttendance, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrAttendance, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def custom_menu(self):
        # views = [(self.env.ref('bi_employee_travel_managment.view_travel_req_tree').id, 'tree'),
        #              (self.env.ref('bi_employee_travel_managment.view_travel_req_form').id, 'form')]
        # search_view_id = self.env.ref("hr_contract.hr_contract_view_search")
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
                    'name': 'Attendances',
                    'res_model': 'hr.attendance',
                    'target': 'current',
                    'view_mode': 'tree,kanban,form',
                    # 'views':views,
                    'domain': [('employee_id', 'in', employee_ids)],
                    'context': {'search_default_today': 1},
                    'help': """<p class="o_view_nocontent_smiling_face">
                        Create new Attendance
                    </p>"""
                    # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                    # 'search_view_id':search_view_id.id,

                }

        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Attendances',
                'res_model': 'hr.attendance',
                'target': 'current',
                'view_mode': 'tree,kanban,form',
                'domain': [],
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create new Attendance
                </p>""",
                'context': {'search_default_today': 1},
                # 'views':views,
                # 'search_view_id':search_view_id.id,
            }


    # @api.depends('employee_id')
    # def _compute_active_location(self):
    #     for rec in self:
    #         if rec.employee_id:
    #             rec.active_location_id = rec.employee_id.active_location
    #         else:
    #             rec.active_location_id = False

           
    
    @api.onchange('check_in')
    def onchange_start_working_date(self):
        for rec in self:
            if rec.check_in:
                employee_tz = rec.employee_id.tz or 'UTC'
                local = pytz.timezone(employee_tz)
                check_in = pytz.UTC.localize(rec.check_in).astimezone(local)
                convert_to_date = fields.Datetime.from_string(check_in.date()).strftime('%Y-%m-%d')
                rec.start_working_date = convert_to_date
    
    @api.depends('check_in')
    def _compute_date_server_checkin(self):
        for rec in self:
            if rec.check_in:
                today = datetime.today().date()
                employee_tz = rec.employee_id.tz or 'UTC'
                local = pytz.timezone(employee_tz)
                check_in = pytz.UTC.localize(rec.check_in).astimezone(local)
                check_in_date = check_in.date()
                if check_in_date < today:
                    return True
                else:
                    if rec.check_in and not rec.is_created:
                        rec.date_server_check_in = datetime.now()
    
    @api.depends('check_out')
    def _compute_date_server_checkout(self):
        for rec in self:
            if rec.check_out:
                today = datetime.today().date()
                employee_tz = rec.employee_id.tz or 'UTC'
                local = pytz.timezone(employee_tz)
                check_out = pytz.UTC.localize(rec.check_out).astimezone(local)
                check_out_date = check_out.date()
                if check_out_date < today:
                    return True
                else:
                    if rec.check_out and not rec.is_created:
                        rec.date_server_check_out = datetime.now()

    @api.depends('employee_id','start_working_date')
    def _compute_working_schedule(self):
        for rec in self:
            schedule = self.env['employee.working.schedule.calendar'].search(
                [('employee_id', '=', rec.employee_id.id), ('date_start', '=', rec.start_working_date)], limit=1)
            if schedule:
                if schedule.working_hours:
                    rec.working_schedule_id = schedule.working_hours
                else:
                    contract = self.env['hr.contract'].search([('employee_id', '=', rec.employee_id.id)], order='id desc', limit=1)
                    if contract:
                        rec.working_schedule_id = contract.resource_calendar_id
                    else:
                        rec.working_schedule_id = False
            else:
                contract = self.env['hr.contract'].search([('employee_id', '=', rec.employee_id.id)], order='id desc', limit=1)
                if contract:
                    rec.working_schedule_id = contract.resource_calendar_id
                else:
                    rec.working_schedule_id = False


    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrAttendance, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_attendance_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        for attendance in self:
            # we take the latest attendance before our check_in time and check it doesn't overlap with ours
            last_attendance_before_check_in = self.env['hr.attendance'].search([
                ('employee_id', '=', attendance.employee_id.id),
                ('check_in', '<=', attendance.check_in),
                ('id', '!=', attendance.id),
            ], order='check_in desc', limit=1)
            # if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out > attendance.check_in:
            #     raise exceptions.ValidationError(
            #         _("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
            #             'empl_name': attendance.employee_id.name,
            #             'datetime': format_datetime(self.env, attendance.check_in, dt_format=False),
            #         })

            if not attendance.check_out:
                # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                no_check_out_attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_out', '=', False),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                # if no_check_out_attendances:
                #     raise exceptions.ValidationError(
                #         _("Cannot create new attendance record for %(empl_name)s, the employee hasn't checked out since %(datetime)s") % {
                #             'empl_name': attendance.employee_id.name,
                #             'datetime': format_datetime(self.env, no_check_out_attendances.check_in, dt_format=False),
                #         })
            else:
                # we verify that the latest attendance with check_in time before our check_out time
                # is the same as the one before our check_in time computed before, otherwise it overlaps
                last_attendance_before_check_out = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '<', attendance.check_out),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                # if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                #     raise exceptions.ValidationError(
                #         _("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                #             'empl_name': attendance.employee_id.name,
                #             'datetime': format_datetime(self.env, last_attendance_before_check_out.check_in,
                #                                         dt_format=False),
                #         })

    @api.depends('start_working_date')
    def _compute_calendar(self):
        for rec in self:
            schedule = self.env['employee.working.schedule.calendar'].search(
                [('employee_id', '=', rec.employee_id.id), ('date_start', '=', rec.start_working_date)], limit=1)
            if schedule:
                rec.calendar_id = schedule.id
                rec.start_working_date = schedule.date_start
                rec.hour_from = schedule.hour_from
                rec.hour_to = schedule.hour_to
                rec.tolerance_late = schedule.tolerance_late
                if schedule.attendance_formula_id:
                    rec.attendance_formula_id = schedule.attendance_formula_id.id
            else:
                rec.calendar_id = False
                rec.hour_from = 0
                rec.hour_to = 0
                rec.tolerance_late = 0
                rec.attendance_formula_id = False

    @api.depends('check_in', 'check_out')
    def _compute_minimum_work_hrs(self):
        for attendance in self:
            if attendance.calendar_id:
                attendance.minimum_hours = attendance.calendar_id.minimum_hours
            else:
                attendance.minimum_hours = 0

    @api.depends('check_in', 'check_out', 'calendar_id')
    def _compute_worked_status(self):
        for attendance in self:
            if attendance.calendar_id:
                checkin_ontime = attendance.calendar_id.checkin + relativedelta(
                    hours=attendance.calendar_id.tolerance_late)
                checkout_ontime = attendance.calendar_id.checkout + relativedelta(
                    hours=attendance.calendar_id.tolerance_late)
                attendance.check_in_diff = 0
                attendance.check_out_diff = 0
                # Checkin Status Calculation
                if attendance.hr_attendance_change_id and attendance.checkin_status_correction:  # if 'My Attendance change req'
                    attendance.checkin_status = attendance.checkin_status_correction
                else:
                    if not attendance.check_in:  # no check in
                        attendance.checkin_status = 'no_checking'
                    elif attendance.check_in < attendance.calendar_id.checkin:  # Early
                        attendance.checkin_status = 'early'
                    elif attendance.check_in > checkin_ontime:  # late
                        attendance.checkin_status = 'late'
                    elif attendance.check_in >= attendance.calendar_id.checkin <= checkin_ontime:  # ontime
                        attendance.checkin_status = 'ontime'

                # Checkin Difference calculation
                if not attendance.check_in:
                    attendance.check_in_diff = attendance.check_in_diff
                elif attendance.check_in < attendance.calendar_id.checkin:  # Early
                    attendance.check_in_diff = (attendance.check_in - checkin_ontime).total_seconds() / 3600
                elif attendance.check_in > checkin_ontime:  # late
                    attendance.check_in_diff = (attendance.check_in - checkin_ontime).total_seconds() / 3600
                else:
                    attendance.check_in_diff = attendance.check_in_diff

                # CheckOut Status Calculation
                if attendance.hr_attendance_change_id and attendance.checkout_status_correction:  # if 'My Attendance change req'
                    attendance.checkout_status = attendance.checkout_status_correction
                else:
                    if not attendance.check_out:
                        attendance.checkout_status = 'no_checkout'
                    elif attendance.worked_hours < attendance.calendar_id.minimum_hours:  # Early
                        attendance.checkout_status = 'early'
                    elif attendance.worked_hours > attendance.calendar_id.minimum_hours:  # late
                        attendance.checkout_status = 'late'
                    elif attendance.worked_hours == attendance.calendar_id.minimum_hours:  # ontime
                        attendance.checkout_status = 'ontime'

                # CheckOut Difference calculation
                if not attendance.check_out:
                    attendance.check_out_diff = attendance.check_out_diff
                elif attendance.check_out < attendance.calendar_id.checkout:  # Early
                    attendance.check_out_diff = (
                                                        attendance.calendar_id.checkout - attendance.check_out).total_seconds() / 3600
                elif attendance.check_out > checkout_ontime:  # late
                    attendance.check_out_diff = (
                                                        attendance.calendar_id.checkout - attendance.check_out).total_seconds() / 3600
                else:
                    attendance.check_out_diff = attendance.check_out_diff

                if attendance.checkin_status == 'early':
                    attendance.early_check_in_diff = (attendance.calendar_id.checkin - attendance.check_in).total_seconds() / 3600
                if attendance.checkout_status == 'early':
                    attendance.early_check_out_diff = (attendance.minimum_hours - attendance.worked_hours)
                if attendance.checkout_status == 'late':
                    attendance.late_check_out_diff = (attendance.worked_hours - attendance.minimum_hours)
            else:
                attendance.checkin_status = ''
                attendance.checkout_status = ''
    
    @api.depends('minimum_hours', 'worked_hours', 'attendance_status')
    def _compute_count_status(self):
        for attendance in self:
            if attendance.worked_hours >= attendance.minimum_hours and not attendance.attendance_status == 'absent':
                attendance.count_status = "fulfilled"
            else:
                attendance.count_status = "not_fulfilled"

    @api.depends('check_in_latitude', 'check_in_longitude', 'check_out_latitude', 'check_out_longitude')
    def _get_address(self):
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

    @api.model
    def _prepare_url(self, url, replace):
        assert url, 'Missing URL'
        for key, value in replace.items():
            if not isinstance(value, str):
                # for latitude and longitude which are floats
                value = str(value)
            url = url.replace(key, value)
        logger.debug('Final URL: %s', url)
        return url

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

    @api.model
    def _cron_update_attendance_status(self):
        setting_update_attendance_status_limit = int(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.update_attendance_status_limit'))
        limit_days = date.today() - relativedelta(days=setting_update_attendance_status_limit)
        employee_data = self.env['hr.employee'].search([('active', '=', True)])
        for emp in split_every(100, employee_data):
            for employee in emp:
                for employee_calendar in self.env['employee.working.schedule.calendar'].search(
                        [('employee_id', '=', employee.id), ('date_start', '>=', limit_days),
                         ('date_start', '<', date.today()),('day_type','!=','day_off')]):
                    if employee_calendar.checkout.date() < date.today():
                        attendance = self.env['hr.attendance'].search(
                            [('employee_id', '=', employee_calendar.employee_id.id),
                             ('start_working_date', '=', employee_calendar.date_start)])
                        for vals in attendance:
                            if vals.attendance_status != 'travel':
                                if not vals.check_in:
                                    vals.attendance_status = 'absent'
                                    vals.is_absent = True
                                if not vals.check_out:
                                    vals.attendance_status = 'absent'
                                    vals.is_absent = True
                        contract = self.env['hr.contract'].search([('employee_id','=',employee_calendar.employee_id.id)], order='id desc', limit=1)
                        if not attendance and not contract.date_end:
                            self.env['hr.attendance'].create({
                                'employee_id': employee.id,
                                'check_in': False,
                                'check_out': False,
                                'start_working_times': employee_calendar.checkin,
                                'start_working_date': employee_calendar.date_start,
                                'calendar_id': employee_calendar.id,
                                'attendance_status': 'absent',
                                'is_absent': True,
                                'is_created': True
                            })
                        elif not attendance and contract.date_end and contract.date_end >= date.today():
                            self.env['hr.attendance'].create({
                                'employee_id': employee.id,
                                'check_in': False,
                                'check_out': False,
                                'start_working_times': employee_calendar.checkin,
                                'start_working_date': employee_calendar.date_start,
                                'calendar_id': employee_calendar.id,
                                'attendance_status': 'absent',
                                'is_absent': True,
                                'is_created': True
                            })
                # one_month = date.today() - relativedelta(months=1)
                for leave in self.env['hr.leave'].search(
                        [('employee_id', '=', employee.id), ('request_date_from', '>=', limit_days),
                         ('request_date_from', '<=', date.today()), ('state', '=', 'validate')]):
                    start_leave = leave.request_date_from
                    while start_leave <= leave.request_date_to:
                        if start_leave <= date.today():
                            attendance_leave = self.env['hr.attendance'].search(
                                [('employee_id', '=', leave.employee_id.id),
                                 ('start_working_date', '=', start_leave)])
                            attendance_leave.leave_type = leave.holiday_status_id.id
                            attendance_leave.attendance_status = leave.holiday_status_id.attendance_status
                            if not attendance_leave:
                                self.env['hr.attendance'].create({
                                    'employee_id': employee.id,
                                    'check_in': False,
                                    'check_out': False,
                                    'start_working_date': start_leave,
                                    'leave_id': leave.id,
                                    'leave_type': leave.holiday_status_id.id,
                                    'attendance_status': leave.holiday_status_id.attendance_status,
                                    'is_created': True
                                })
                        start_leave += relativedelta(days=1)
                for attendance in self.env['hr.attendance'].search(
                        [('employee_id', '=', employee.id), ('is_created', '!=', True), ('active', '=', True)]):
                    attendance_checkin = self.env['hr.attendance'].search(
                        [('employee_id', '=', employee.id), ('start_working_date', '=', attendance.start_working_date)],
                        order='check_in', limit=1)
                    attendance_checkout = self.env['hr.attendance'].search(
                        [('employee_id', '=', employee.id), ('start_working_date', '=', attendance.start_working_date)],
                        order='check_out desc', limit=1)
                    check_in = attendance_checkin.check_in
                    check_out = attendance_checkout.check_out
                    date_server_check_in = attendance_checkin.date_server_check_in
                    date_server_check_out = attendance_checkout.date_server_check_out
                    check_in_latitude = attendance_checkin.check_in_latitude
                    check_in_longitude = attendance_checkin.check_in_longitude
                    check_in_address = attendance_checkin.check_in_address
                    check_out_latitude = attendance_checkout.check_out_latitude
                    check_out_longitude = attendance_checkout.check_out_longitude
                    check_out_address = attendance_checkout.check_out_address

                    face_recognition_image_check_in = attendance_checkin.face_recognition_image_check_in
                    face_recognition_image_check_out = attendance_checkout.face_recognition_image_check_out
                    face_recognition_access_check_in = attendance_checkin.face_recognition_access_check_in
                    face_recognition_access_check_out = attendance_checkout.face_recognition_access_check_out
                    webcam_check_in = attendance_checkin.webcam_check_in
                    webcam_check_out = attendance_checkout.webcam_check_out

                    attendance_exist = self.env['hr.attendance'].search(
                        [('employee_id', '=', attendance.employee_id.id),
                         ('start_working_date', '=', attendance.start_working_date), ('is_created', '=', True),
                         ('active', '=', True)])
                    if not attendance_exist:
                        if not check_out or check_out and check_out >= check_in:
                            attendance_data = self.env['hr.attendance'].search(
                                [('employee_id', '=', attendance.employee_id.id), 
                                 ('start_working_date', '=', attendance.start_working_date), 
                                 ('active', '=', True)])

                            location_list = attendance_data.active_location_id.ids

                            vals = {
                                'employee_id': employee.id,
                                'check_in': check_in,
                                'check_out': check_out,
                                'date_server_check_in': date_server_check_in,
                                'date_server_check_out': date_server_check_out,
                                'face_recognition_image_check_in': face_recognition_image_check_in,
                                'face_recognition_image_check_out': face_recognition_image_check_out,
                                'face_recognition_access_check_in': face_recognition_access_check_in,
                                'face_recognition_access_check_out': face_recognition_access_check_out,
                                'webcam_check_in': webcam_check_in,
                                'webcam_check_out': webcam_check_out,
                                'start_working_date': attendance.start_working_date,
                                'is_created': True,
                                'attendance_status': 'absent',
                                'check_in_latitude': check_in_latitude,
                                'check_in_longitude': check_in_longitude,
                                'check_in_address': check_in_address,
                                'check_out_latitude': check_out_latitude,
                                'check_out_longitude': check_out_longitude,
                                'check_out_address': check_out_address,
                                'active_location_id': [(6,0, location_list)],
                            }

                            if check_in:
                                vals['attendance_status'] = 'present'

                            self.env['hr.attendance'].create(vals)
                    if not attendance.check_out or attendance.check_out and attendance.check_out >= attendance.check_in:
                        attendance.active = False
            self._cr.commit()
        self.sub_cron_attendance_absent()
        self.sub_cron_delete_archived_attendance()

    @api.model
    def _cron_update_employee_calendar(self):
        one_week = date.today() - relativedelta(weeks=1)
        one_month = date.today() - relativedelta(days=30)
        for employee in self.env['hr.employee'].search(
                [('active', '=', True), ('contract_id.date_start', '>=', one_month)]):
            calendar = self.env['hr.generate.workingcalendar'].search(
                [('employee_ids', 'in', employee.id), ('date', '>=', one_week)])
            if not calendar:
                current_year = date.today().year
                working_calendar = self.env['hr.generate.workingcalendar'].create({
                    'generate_type': 'create_update',
                    'employee_ids': employee.ids,
                    'follow_contract_period': False,
                    'start_date': employee.contract_id.date_start,
                    'end_date': employee.contract_id.date_end or date(current_year, 12, 31),
                })
                working_calendar.action_generate()
        self.sub_cron_update_working_calendar()

    def sub_cron_update_working_calendar(self):
        one_week = date.today() - relativedelta(weeks=1)
        contract_rec = self.env['hr.contract'].search([('state', '=', 'open')])
        if contract_rec:
            for contract in contract_rec:
                if contract.employee_id:
                    calendar = self.env['hr.generate.workingcalendar'].search([('employee_ids', 'in', contract.employee_id.id), ('date', '>=', one_week)])
                    if not calendar:
                        current_year = date.today().year
                        working_calendar = self.env['hr.generate.workingcalendar'].create({
                            'generate_type': 'create_update',
                            'employee_ids': contract.employee_id.ids,
                            'follow_contract_period': False,
                            'start_date': contract.date_start,
                            'end_date': contract.date_end or date(current_year, 12, 31),
                        })
                        working_calendar.action_generate()


    def sub_cron_attendance_absent(self):
        self.filter_group_by_managers()
        self.filter_group_by_managers_min()
        current_date = date.today()

        for attendance in self.env['hr.attendance'].search(
                [('employee_id.active', '=', True), ('is_absent', '=', True), ('is_absent_email_sent', '!=', True),
                 ('active', '=', True), ('attendance_status', '=', 'absent')]):
            attendance.attendance_absent_mail()
            # attendance.attendance_notify_absent_mail()
            attendance.attendance_absent_wa()
            # attendance.attendance_notify_absent_wa()
            attendance.is_absent = False
            attendance.is_absent_email_sent = True

        for attendance in self.env['hr.attendance'].search([('employee_id.active', '=', True), ('active', '=', True)]):
            one_day = attendance.start_working_date + relativedelta(days=1)
            if one_day == current_date and attendance.minimum_hours > attendance.worked_hours:
                attendance.attendance_working_under_minimum_hours_mail()
                # attendance.attendance_notify_working_under_minimum_hours_mail()
                attendance.attendance_working_under_minimum_hours_wa()
                # attendance.attendance_notify_working_under_minimum_hours_wa()

    def sub_cron_delete_archived_attendance(self):
        one_month = date.today() - relativedelta(days=30)
        attendance = self.env['hr.attendance'].search([('active', '=', False), ('start_working_date', '<=', one_month)])
        if attendance:
            attendance.unlink()


    def attendance_absent_mail(self):
        ir_model_data = self.env['ir.model.data']
        template_id = ir_model_data.get_object_reference('equip3_hr_attendance_extend', 'email_template_attendance_absent')[1]
        ctx = self._context.copy()
        ctx.update({
            'email_from': self.env.user.email,
            'email_to': self.employee_id.user_id.email,
        })
        if self.start_working_date:
            ctx.update(
                {'working_date': fields.Datetime.from_string(self.start_working_date).strftime('%d/%m/%Y')})
        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                  force_send=True)

    # def attendance_notify_absent_mail(self):
    #     ir_model_data = self.env['ir.model.data']
    #     template_id = ir_model_data.get_object_reference('equip3_hr_attendance_extend', 'email_template_notify_attendance_absent')[1]
    #     ctx = self._context.copy()
    #     ctx.update({
    #         'email_from': self.env.user.email,
    #         'email_to': self.employee_id.parent_id.user_id.email,
    #     })
    #     if self.start_working_date:
    #         ctx.update(
    #             {'working_date': fields.Datetime.from_string(self.start_working_date).strftime('%d/%m/%Y')})
    #     self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
    #                                                                               force_send=True)

    def attendance_working_under_minimum_hours_mail(self):
        ir_model_data = self.env['ir.model.data']
        template_id = ir_model_data.get_object_reference('equip3_hr_attendance_extend', 'email_template_working_under_minimum_hours')[1]
        ctx = self._context.copy()
        ctx.update({
            'email_from': self.env.user.email,
            'email_to': self.employee_id.user_id.email,
        })
        if self.start_working_date:
            ctx.update(
                {'working_date': fields.Datetime.from_string(self.start_working_date).strftime('%d/%m/%Y')})
        if self.minimum_hours:
            ctx.update(
                {'minimum_hrs': round(self.minimum_hours, 2)})
        if self.worked_hours:
            ctx.update(
                {'worked_hrs': round(self.worked_hours, 2)})
        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                  force_send=True)

    # def attendance_notify_working_under_minimum_hours_mail(self):
    #     ir_model_data = self.env['ir.model.data']
    #     template_id = ir_model_data.get_object_reference('equip3_hr_attendance_extend', 'email_template_notify_working_under_minimum_hours')[1]
    #     ctx = self._context.copy()
    #     ctx.update({
    #         'email_from': self.env.user.email,
    #         'email_to': self.employee_id.parent_id.user_id.email,
    #     })
    #     if self.start_working_date:
    #         ctx.update(
    #             {'working_date': fields.Datetime.from_string(self.start_working_date).strftime('%d/%m/%Y')})
    #     if self.minimum_hours:
    #         ctx.update(
    #             {'minimum_hrs': round(self.minimum_hours, 2)})
    #     if self.worked_hours:
    #         ctx.update(
    #             {'worked_hrs': round(self.worked_hours, 2)})
    #     self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
    #                                                                               force_send=True)


    def attendance_absent_wa(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        if send_by_wa:
            wa_sender = waParam()
            template = self.env.ref('equip3_hr_attendance_extend.attendance_absent_wa_template')
            if template:
                string_test = str(template.message)
                if "${employee_name}" in string_test:
                    string_test = string_test.replace("${employee_name}", self.employee_id.name)
                if self.start_working_date:
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.start_working_date).strftime('%d/%m/%Y'))
                if "${br}" in string_test:
                    string_test = string_test.replace("${br}", f"\n")
                phone_num = str(self.employee_id.mobile_phone)
                if "+" in phone_num:
                    phone_num = int(phone_num.replace("+", ""))

                wa_sender.set_wa_string(template.message,template._name,template_id=template)
                wa_sender.send_wa(phone_num)
                
        #         param = {'body': string_test, 'phone': phone_num}
        #         domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
        #         token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
        #         try:
        #             request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
        #                                            headers=headers, verify=True)
        #         except ConnectionError:
        #             raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    # def attendance_notify_absent_wa(self):
    #     send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
    #     if send_by_wa:
    #         template = self.env.ref('equip3_hr_attendance_extend.attendance_notify_absent_wa_template')
    #         if template:
    #             string_test = str(template.message)
    #             if "${employee_name}" in string_test:
    #                 string_test = string_test.replace("${employee_name}", self.employee_id.name)
    #             if "${approver_name}" in string_test:
    #                 string_test = string_test.replace("${approver_name}", self.employee_id.parent_id.name)
    #             if self.start_working_date:
    #                 if "${start_date}" in string_test:
    #                     string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
    #                         self.start_working_date).strftime('%d/%m/%Y'))
    #             if "${br}" in string_test:
    #                 string_test = string_test.replace("${br}", f"\n")
    #             phone_num = str(self.employee_id.parent_id.mobile_phone)
    #             if "+" in phone_num:
    #                 phone_num = int(phone_num.replace("+", ""))
    #             param = {'body': string_test, 'phone': phone_num}
    #             domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
    #             token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
    #             try:
    #                 request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
    #                                                headers=headers, verify=True)
    #             except ConnectionError:
    #                 raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def attendance_working_under_minimum_hours_wa(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        if send_by_wa:
            wa_sender = waParam()

            template = self.env.ref('equip3_hr_attendance_extend.attendance_working_under_minimum_hours_wa_template')
            if template:
                string_test = str(template.message)
                if "${employee_name}" in string_test:
                    string_test = string_test.replace("${employee_name}", self.employee_id.name)
                if self.start_working_date:
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.start_working_date).strftime('%d/%m/%Y'))
                if "${worked_hrs}" in string_test:
                    wh = round(self.worked_hours, 2)
                    string_test = string_test.replace("${worked_hrs}", str(wh))
                if "${minimum_hrs}" in string_test:
                    mh = round(self.minimum_hours, 2)
                    string_test = string_test.replace("${minimum_hrs}", str(mh))
                phone_num = str(self.employee_id.mobile_phone)
                if "+" in phone_num:
                    phone_num = int(phone_num.replace("+", ""))
                wa_sender.set_wa_string(template.message,template._name,template_id=template)
                wa_sender.send_wa(phone_num)

    # def attendance_notify_working_under_minimum_hours_wa(self):
    #     send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
    #     if send_by_wa:
    #         template = self.env.ref('equip3_hr_attendance_extend.attendance_notify_working_under_minimum_hours_wa_template')
    #         if template:
    #             string_test = str(template.message)
    #             if "${employee_name}" in string_test:
    #                 string_test = string_test.replace("${employee_name}", self.employee_id.name)
    #             if "${approver_name}" in string_test:
    #                 string_test = string_test.replace("${approver_name}", self.employee_id.parent_id.name)
    #             if self.start_working_date:
    #                 if "${start_date}" in string_test:
    #                     string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
    #                         self.start_working_date).strftime('%d/%m/%Y'))
    #             if "${worked_hrs}" in string_test:
    #                 wh = round(self.worked_hours, 2)
    #                 string_test = string_test.replace("${worked_hrs}", str(wh))
    #             if "${minimum_hrs}" in string_test:
    #                 mh = round(self.minimum_hours, 2)
    #                 string_test = string_test.replace("${minimum_hrs}", str(mh))
    #             if "${br}" in string_test:
    #                 string_test = string_test.replace("${br}", f"\n")
    #             phone_num = str(self.employee_id.parent_id.mobile_phone)
    #             if "+" in phone_num:
    #                 phone_num = int(phone_num.replace("+", ""))
    #             param = {'body': string_test, 'phone': phone_num}
    #             domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
    #             token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
    #             try:
    #                 request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
    #                                                headers=headers, verify=True)
    #             except ConnectionError:
    #                 raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def remove_att_email(self):
        for att_email in self.env['hr.att.email'].search([]):
            if att_email:
                remove = []
                for line in att_email.attendance_line_ids:
                    remove.append((2, line.id))
                att_email.attendance_line_ids = remove
                att_email.unlink()

    def filter_group_by_managers(self):
        self.remove_att_email()
        sql = "INSERT INTO hr_att_email (parent_id) SELECT manager_id FROM hr_attendance where manager_id IS NOT NULL GROUP BY manager_id"
        self.env.cr.execute(sql)
        for attendance in self.env['hr.attendance'].search(
                [('employee_id.active', '=', True), ('is_absent', '=', True), ('is_absent_email_sent', '!=', True),
                 ('active', '=', True), ('attendance_status', '=', 'absent')]):
            for att_email in self.env['hr.att.email'].search([('parent_id', '=', attendance.manager_id.id)], limit=1):
                self.env['hr.att.email.line'].create({
                    'hr_att_email_id': att_email.id,
                    'attendance_id': attendance.id,
                })
        for att_email in self.env['hr.att.email'].search([]):
            if att_email and att_email.attendance_line_ids:
                att_email.attendance_notify_absent_mail()
                att_email.attendance_notify_absent_wa()
                remove = []
                for line in att_email.attendance_line_ids:
                    remove.append((2, line.id))
                att_email.attendance_line_ids = remove
                att_email.unlink()

    def filter_group_by_managers_min(self):
        self.remove_att_email()
        current_date = date.today()
        sql = "INSERT INTO hr_att_email (parent_id) SELECT manager_id FROM hr_attendance where manager_id IS NOT NULL GROUP BY manager_id"
        self.env.cr.execute(sql)
        for attendance in self.env['hr.attendance'].search([('employee_id.active', '=', True), ('active', '=', True)]):
            one_day = attendance.start_working_date + relativedelta(days=1)
            if one_day == current_date and attendance.minimum_hours > attendance.worked_hours:
                for att_email in self.env['hr.att.email'].search([('parent_id', '=', attendance.manager_id.id)],
                                                                 limit=1):
                    self.env['hr.att.email.line'].create({
                        'hr_att_email_id': att_email.id,
                        'attendance_id': attendance.id,
                    })
        for att_email in self.env['hr.att.email'].search([]):
            if att_email and att_email.attendance_line_ids:
                att_email.attendance_notify_working_under_minimum_hours_mail()
                att_email.attendance_notify_working_under_minimum_hours_wa()
                remove = []
                for line in att_email.attendance_line_ids:
                    remove.append((2, line.id))
                att_email.attendance_line_ids = remove
                att_email.unlink()

    def generate_calendar(self):
        for rec in self:
            if rec.is_imported:
                wrk_calendar = self.env['employee.working.schedule.calendar'].search(
                    [('employee_id', '=', rec.employee_id.id), ('active', '=', True),
                     ('date_start', '=', rec.start_working_date)], limit=1)
                if not wrk_calendar:
                    grt_calendar = self.env['hr.generate.workingcalendar'].create({
                        'generate_type': 'create_update',
                        'follow_contract_period': False,
                        'start_date': rec.start_working_date,
                        'end_date': rec.start_working_date,
                        'state': 'draft',
                        'employee_ids': rec.employee_id,
                    })
                    grt_calendar.action_generate()

    @api.model
    def create(self, vals):
        res = super(HrAttendance, self).create(vals)
        res.generate_calendar()
        res.onchange_start_working_date()
        res._compute_calendar()
        return res

    @api.constrains('is_imported')
    def _check_contract(self):
        for rec in self:
            contract = self.env['hr.contract'].search(
                [('employee_id', '=', rec.employee_id.id), ('state', '=', 'open'), ('active', '=', True)],
                order='id desc', limit=1)
            if not contract and rec.is_imported:
                raise ValidationError("(%s) does not have a running contract" % rec.employee_id.name)

    @api.depends('check_in', 'check_out', 'calendar_id')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in and attendance.calendar_id:
                delta = attendance.check_out - attendance.check_in
                if attendance.calendar_id.working_hours.break_time_to_work_hour:
                    break_time = attendance.calendar_id.break_to - attendance.calendar_id.break_from
                    worked_hours = (delta.total_seconds() / 3600.0) - break_time
                    attendance.worked_hours = worked_hours
                else:
                     attendance.worked_hours = delta.total_seconds() / 3600.0
            elif attendance.check_out and attendance.check_in:
                delta = attendance.check_out - attendance.check_in
                attendance.worked_hours = delta.total_seconds() / 3600.0
            else:
                attendance.worked_hours = False

class resource_calendar_attendance_in(models.Model):
    _inherit = 'resource.calendar.attendance'

    minimum_hours = fields.Float(string='Minimum Hours', required=0)


class HrAttEmail(models.Model):
    _name = "hr.att.email"

    name = fields.Char()
    parent_id = fields.Many2one('hr.employee', string='Manager')
    start_working_date = fields.Date(string='Working Date')
    attendance_line_ids = fields.One2many('hr.att.email.line', 'hr_att_email_id')
    whatsapp_meassage = fields.Text('Absent WhatsApp Meassage')

    def fetch_start_working_date(self):
        for rec in self:
            line = self.attendance_line_ids[0]
            rec.start_working_date = line.attendance_id.start_working_date

    def update_wa_msg1(self):
        for rec in self:
            rec.whatsapp_meassage = False
            rec.whatsapp_meassage = ''
            string_approval = []
            string_approval.append(rec.whatsapp_meassage)
            for line in rec.attendance_line_ids:
                seq = str(line.name)
                name = str(line.attendance_id.employee_id.name)
                msg = seq + '.' + ' ' + name
                string_approval.append(f"{msg}")
                rec.whatsapp_meassage = "\n".join(string_approval)

    def update_wa_msg2(self):
        for rec in self:
            rec.whatsapp_meassage = False
            rec.whatsapp_meassage = ''
            string_approval = []
            string_approval.append(rec.whatsapp_meassage)
            for line in rec.attendance_line_ids:
                seq = str(line.name)
                name = str(line.attendance_id.employee_id.name)
                wk_hrs = str(line.worked_hours)
                min_hrs = str(line.minimum_hours)
                msg = seq + '.' + ' ' + name + ',' + 'only working ' + wk_hrs + ' And have to work for' + ' ' + min_hrs + ' hours.'
                string_approval.append(f"{msg}")
                rec.whatsapp_meassage = "\n".join(string_approval)


    def attendance_notify_absent_mail(self):
        self.fetch_start_working_date()
        ir_model_data = self.env['ir.model.data']
        template_id = ir_model_data.get_object_reference('equip3_hr_attendance_extend', 'email_template_notify_attendance_absent')[1]
        ctx = self._context.copy()
        ctx.update({
            'email_from': self.env.user.email,
            'email_to': self.parent_id.user_id.email,
        })
        if self.start_working_date:
            ctx.update(
                {'working_date': fields.Datetime.from_string(self.start_working_date).strftime('%d/%m/%Y')})
        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                  force_send=True)

    def attendance_notify_absent_wa(self):
        self.fetch_start_working_date()
        self.update_wa_msg1()
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_extend.attendance_notify_absent_wa_template')
            if template:
                string_test = str(template.message)
                if "${employee_name}" in string_test:
                    string_test = string_test.replace("${employee_name}", self.whatsapp_meassage)
                if "${approver_name}" in string_test:
                    string_test = string_test.replace("${approver_name}", self.parent_id.name)
                if self.start_working_date:
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.start_working_date).strftime('%d/%m/%Y'))
                if "${br}" in string_test:
                    string_test = string_test.replace("${br}", f"\n")
                phone_num = str(self.parent_id.mobile_phone)
                if "+" in phone_num:
                    phone_num = int(phone_num.replace("+", ""))
                param = {'body': string_test, 'phone': phone_num}
                domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                try:
                    request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                                                   headers=headers, verify=True)
                except ConnectionError:
                    raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def attendance_notify_working_under_minimum_hours_mail(self):
        self.fetch_start_working_date()
        ir_model_data = self.env['ir.model.data']
        template_id = ir_model_data.get_object_reference('equip3_hr_attendance_extend', 'email_template_notify_working_under_minimum_hours')[1]
        ctx = self._context.copy()
        ctx.update({
            'email_from': self.env.user.email,
            'email_to': self.parent_id.user_id.email,
        })
        if self.start_working_date:
            ctx.update(
                {'working_date': fields.Datetime.from_string(self.start_working_date).strftime('%d/%m/%Y')})
        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                  force_send=True)

    def attendance_notify_working_under_minimum_hours_wa(self):
        self.fetch_start_working_date()
        self.update_wa_msg2()
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_extend.attendance_notify_working_under_minimum_hours_wa_template')
            if template:
                string_test = str(template.message)
                if "${employee_name}" in string_test:
                    string_test = string_test.replace("${employee_name}", self.whatsapp_meassage)
                if "${approver_name}" in string_test:
                    string_test = string_test.replace("${approver_name}", self.parent_id.name)
                if self.start_working_date:
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.start_working_date).strftime('%d/%m/%Y'))
                if "${br}" in string_test:
                    string_test = string_test.replace("${br}", f"\n")
                phone_num = str(self.parent_id.mobile_phone)
                if "+" in phone_num:
                    phone_num = int(phone_num.replace("+", ""))
                param = {'body': string_test, 'phone': phone_num}
                domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                try:
                    request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                                                   headers=headers, verify=True)
                except ConnectionError:
                    raise ValidationError("Not connect to API Chat Server. Limit reached or not active")


class HrAttEmailLine(models.Model):
    _name = 'hr.att.email.line'

    hr_att_email_id = fields.Many2one('hr.att.email')
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    attendance_id = fields.Many2one('hr.attendance', string='Attendance')
    minimum_hours = fields.Char(string='Minimum Hours')
    worked_hours = fields.Char(string='Minimum Hours')


    @api.depends('hr_att_email_id')
    def fetch_sl_no(self):
        sl = 0
        for rec in self:
            rec.minimum_hours = round(rec.attendance_id.minimum_hours, 2)
            rec.worked_hours = round(rec.attendance_id.worked_hours, 2)
        for line in self.hr_att_email_id.attendance_line_ids:
            sl = sl + 1
            line.name = sl