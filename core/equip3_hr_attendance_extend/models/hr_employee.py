# -*- coding: utf-8 -*-
from geopy import distance
from odoo import api, fields, models, _
from datetime import date, datetime
import pytz
from dateutil.relativedelta import relativedelta
from urllib.request import urlopen
from odoo.http import request
import json
from requests import get
import whatismyip
import time
import random
from odoo.exceptions import ValidationError

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    active_location = fields.Many2many('res.partner', string="Active Location", help="active location new")
    allow_offline_attendance = fields.Boolean(string="Allow Offline Attendance")
    active_location_ids = fields.One2many('active.location', 'employee_id')
    selected_active_location_id = fields.Many2one('active.location')
    auto_submit_data_record = fields.Boolean(string="Auto Submit Data Record")
    attendance_id_pin = fields.Char('Attendance ID', readonly=True, copy=False)
    is_use_reason = fields.Boolean(default=False)
    notes_reason = fields.Text()
    reason_categ = fields.Many2one('hr.attendance.reason.categ')
    

    _sql_constraints = [
        ('attendance_id_pin_uniq', 'unique (attendance_id_pin)', 'Attendance pin must be unique per user'),
    ]
    
    
    def set_use_reason(self,**kw):
        location_id = kw.get('selected_active_location_id')
        location_object_id = self.env['active.location'].search([('id','=',location_id)],limit=1)
        return location_object_id.active_location_id.is_use_att_reason

    def read(self, fields=None, load='_classic_read'):
        res = super(HrEmployee, self).read(fields, load)
        user = self.env.user
        disable_masking = self.env.context.get('attendance_id_pin_disable_masking', False)
        if 'attendance_id_pin' in fields and not disable_masking:
            for record in res:
                employee = self.env['hr.employee'].browse(record.get('id'))
                if employee.user_id.id != user.id:
                    record['attendance_id_pin'] = '******'
        return res

    @api.model
    def create(self, vals):
        if 'attendance_id_pin' in vals and vals['attendance_id_pin'] == '******':
            del vals['attendance_id_pin']
        return super(HrEmployee, self).create(vals)

    def write(self, vals):
        if 'attendance_id_pin' in vals and vals['attendance_id_pin'] == '******':
            del vals['attendance_id_pin']
        return super(HrEmployee, self).write(vals)

    def save_selected_location(self, vals):
        if not self.active_location_ids:
            vals['active_location_ids'] = [(4, vals['selected_active_location_id'])]
        return self.write(vals)

    def generate_unique_six_digit(self):
        timestamp = int(time.time()) % 1000000  # Get last 6 digits of the current timestamp
        random_offset = random.randint(0, 999)  # Add some randomness
        return (timestamp + random_offset) % 1000000

    def make_sure_the_pin_is_unique(self, list_unique_id):
        pin = self.generate_unique_six_digit()
        if pin in list_unique_id:
            return self.make_sure_the_pin_is_unique(list_unique_id)
        return pin

    def get_random_numbers(self, employee_count):
        list_unique_id = []
        for _ in range(0, employee_count):
            pin = self.make_sure_the_pin_is_unique(list_unique_id)
            list_unique_id.append(pin)
        employee_found = self.env['hr.employee'].search([('attendance_id_pin', 'in', list_unique_id)])
        if employee_found:
            return self.get_random_numbers(employee_count)
        return list_unique_id

    @api.model
    def generate_attendace_id_pin(self):
        employees = self.env['hr.employee'].search([('attendance_id_pin', '=', False)])
        if employees:
            random_numbers = self.get_random_numbers(len(employees))
            for employee, unique_number in zip(employees, random_numbers):
                employee.write({
                    'attendance_id_pin': str(unique_number)
                })

    @api.model
    def match_attendance_id_pin(self, attendance_id_pin_val):
        employee = self.env['hr.employee'].sudo().search_read(
            [('attendance_id_pin', '=', attendance_id_pin_val)], ['id', 'name']
        )
        return employee

    @api.constrains('active_location_ids')
    def _check_active_location_ids(self):
        for rec in self:
            if rec.active_location_ids:
                default_count = 0
                for location in rec.active_location_ids:
                    if location.is_default:
                        default_count += 1
                    if default_count > 1:
                        raise ValidationError(_('Only 1 Default Active Location is Allowed'))

                if default_count == 0:
                    raise ValidationError(_('Please Define 1 Active Location as Default Value'))

    def _compute_hours_today(self):
        for employee in self:
            now = fields.Datetime.now()
            now_utc = pytz.utc.localize(now)
            query = """
            select ha.id,ha.check_in,ha.check_out from hr_attendance ha WHERE ha.employee_id = %s ORDER BY ID DESC LIMIT 1
            """
            request._cr.execute(query, [employee.id])
            my_attendance = request.env.cr.dictfetchone()
            localtz = pytz.timezone(self.env.user.tz if self.env.user.tz else'Asia/Jakarta')
            # start of day in the employee's timezone might be the previous day in utc
            tz = pytz.timezone(employee.tz)
            now_tz = now_utc.astimezone(tz)
            start_tz = now_tz + relativedelta(hour=0, minute=0)  # day start in the employee's timezone
            start_naive = start_tz.astimezone(pytz.utc).replace(tzinfo=None)
            attendances = False
            if my_attendance:
                attendances = self.env['hr.attendance'].browse([my_attendance['id']])

            worked_hours = 0
            if attendances:
                for attendance in attendances:
                    # if attendance.check_in:
                    #     max_checkin = max(attendance.check_in, start_naive)
                    # else:
                    max_checkin = attendance.check_in
                    # delta = (attendance.check_out or now) - max(attendance.check_in, start_naive)
                    if max_checkin:
                        delta = now - max_checkin
                        worked_hours += delta.total_seconds() / 3600.0
            employee.hours_today = worked_hours

    @api.depends('attendance_ids')
    def _compute_last_attendance_id(self):
        for employee in self:
            employee.last_attendance_id = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),('active', '=', True)
            ],order="id desc", limit=1)
            
    @api.depends('last_attendance_id.check_in', 'last_attendance_id.check_out', 'last_attendance_id')
    def _compute_attendance_state(self):
        for employee in self:
            att = employee.last_attendance_id.sudo()
            now = datetime.now()
            if att and att.check_in and not att.check_out:
                if att.calendar_id.start_checkin and att.calendar_id.end_checkout:
                    if now >= att.calendar_id.start_checkin and now <= att.calendar_id.end_checkout:
                        employee.attendance_state = 'checked_in'
                    else:
                        employee.attendance_state = 'checked_out'
                else:
                    if att.start_working_date == date.today():
                        employee.attendance_state = 'checked_in'
                    else:
                        employee.attendance_state = 'checked_out'
            else:
                employee.attendance_state = 'checked_out'

    def attendance_manual(self, next_action, entered_pin=False, location=False):
        res = super(HrEmployee, self.with_context(att_location=location)).attendance_manual(next_action, entered_pin)
        return res
    
    def checkin_checkout_availabilty(self, entered_pin=False, location=False):
        latitude = float(location[0])
        longitude = float(location[1])
        params = self.env['ir.config_parameter'].sudo()
        if latitude is not None and longitude is not None:
            if self.active_location_ids and self.selected_active_location_id:
                att_range = int(self.selected_active_location_id.active_location_id.attendance_range)
                act_latitude = self.selected_active_location_id.active_location_id.partner_latitude
                act_longitude = self.selected_active_location_id.active_location_id.partner_longitude
                if act_latitude and act_longitude:
                    pdistance = distance.distance((act_latitude, act_longitude), (latitude, longitude)).km
                    ip_public = whatismyip.whatismyipv4()
                    url_ipinfo = 'http://ipinfo.io/'+str(ip_public)+'/json'
                    response_ipinfo = urlopen(url_ipinfo)
                    data_ipinfo = json.load(response_ipinfo)

                    location_ip = data_ipinfo.get('loc') or False
                    ipinfo_latitude = location_ip.split(',')[0]
                    ipinfo_longitude = location_ip.split(',')[1]
                    fakepdistance = distance.distance((latitude, longitude), (float(ipinfo_latitude), float(ipinfo_longitude))).km
                    if (fakepdistance * 1000) <= 8000:
                        fakegps = False
                    else:
                        return {
                            'toast_type': 'danger',
                            'toast_content': _("Please do not use Fake GPS and VPN.")
                        }

                    if att_range == 0:
                        return {
                            'toast_type': 'info',
                            'toast_content':_("You are in Valid Location to do Check In | Check Out")
                        }
                    elif (pdistance * 1000) <= att_range:
                        return {
                            'toast_type': 'info',
                            'toast_content':_("You are in Valid Location to do Check In | Check Out")
                        }
                    else:
                        return {
                            'toast_type': 'danger',
                            'toast_content': _("You can only do check in/out within Active Location range")
                        }
                else:
                    return {
                            'toast_type': 'info',
                            'toast_content':_("You are in Valid Location to do Check In | Check Out")
                        }

    def _attendance_action(self, next_action):
        """ Changes the attendance of the employee.
            Returns an action to the check in/out message,
            next_action defines which menu the check in/out message should return to. ("My Attendances" or "Kiosk Mode")
        """
        self.ensure_one()
        employee = self.sudo()
        action_message = self.env["ir.actions.actions"]._for_xml_id("hr_attendance.hr_attendance_action_greeting_message")
        action_message['previous_attendance_change_date'] = employee.last_attendance_id and (employee.last_attendance_id.check_out or employee.last_attendance_id.check_in) or False
        action_message['employee_name'] = employee.name
        action_message['barcode'] = employee.barcode
        action_message['next_action'] = next_action
        action_message['hours_today'] = employee.hours_today
        # Checking Active Location range
        location = self.env.context.get("att_location")
        latitude = float(location[0])
        longitude = float(location[1])
        params = self.env['ir.config_parameter'].sudo()
        if latitude is not None and longitude is not None:
            try:
                if not self.active_location_ids:
                    if employee.user_id:
                        modified_attendance = employee.with_user(employee.user_id)._attendance_action_change()
                    else:
                        modified_attendance = employee._attendance_action_change()
                    action_message['attendance'] = modified_attendance.read()[0]
                    return {'action':action_message}
                if self.active_location_ids and self.selected_active_location_id:
                    att_range = int(self.selected_active_location_id.active_location_id.attendance_range)
                    act_latitude = self.selected_active_location_id.active_location_id.partner_latitude
                    act_longitude = self.selected_active_location_id.active_location_id.partner_longitude
                    if act_latitude and act_longitude:
                        pdistance = distance.distance((act_latitude, act_longitude), (latitude, longitude)).km

                        ip_public = whatismyip.whatismyipv4()
                        url_ipinfo = 'http://ipinfo.io/'+str(ip_public)+'/json'
                        response_ipinfo = urlopen(url_ipinfo)
                        data_ipinfo = json.load(response_ipinfo)
                    
                        location_ip = data_ipinfo.get('loc') or False
                        ipinfo_latitude = location_ip.split(',')[0]
                        ipinfo_longitude = location_ip.split(',')[1]
                        fakepdistance = distance.distance((latitude, longitude), (float(ipinfo_latitude), float(ipinfo_longitude))).km
                        if (fakepdistance * 1000) <= 8000:
                            fakegps = False
                        else:
                            return {'warning': _("Please do not use Fake GPS and VPN.")}

                        if (att_range == 0) or ((pdistance * 1000) <= att_range):
                            if employee.user_id:
                                modified_attendance = employee.with_user(employee.user_id)._attendance_action_change()
                            else:
                                modified_attendance = employee._attendance_action_change()
                            action_message['attendance'] = modified_attendance.read()[0]
                            return {'action': action_message}
                        else:
                
                            return {'warning': _("You can only do check in/out within Active Location range")}
                    else:
                        if employee.user_id:
                            modified_attendance = employee.with_user(employee.user_id)._attendance_action_change()
                        else:
                            modified_attendance = employee._attendance_action_change()
                        action_message['attendance'] = modified_attendance.read()[0]
                        return {'action': action_message}
            except ValidationError as err:
                return {'warning': f'{err}'}
        else:
            return {'action': action_message}

    def _attendance_action_change(self):
        self.ensure_one()
        action_date = fields.Datetime.now()
        location = self.env.context.get("att_location", False)
        att = self.last_attendance_id.sudo()

        tz = pytz.timezone(self.tz)
        now_tz = datetime.now().astimezone(tz)
        date_today = now_tz.date()

        schedule = self.env['employee.working.schedule.calendar'].search(
            [('employee_id', '=', self.id),('date_start', '=', date_today)], limit=1)
        if schedule.start_checkin and schedule.end_checkout:
            checked_in_time = datetime.now() >= schedule.start_checkin and datetime.now() <= schedule.end_checkout
            if self.attendance_state != 'checked_in' and not checked_in_time:
                raise ValidationError(_('You cannot check in now.'))

        if self.attendance_state != 'checked_in':
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
            }
            if self.is_use_reason:
                vals['check_in_reason_categ'] = self.reason_categ.id
                vals['check_in_notes'] = self.notes_reason
            if self.active_location_ids and self.selected_active_location_id:
                vals['active_location_id'] = [(4, self.selected_active_location_id.active_location_id.id)]
            if location:
                vals.update(
                {
                     "check_in_latitude": location[0],
                        "check_in_longitude": location[1],
                }
            )
            self.parse_param(vals)

            HrAttendance = self.env['hr.attendance'].search([('employee_id','=',self.id),('start_working_date','=',date.today()),('check_in','=',False)], limit=1)
            if HrAttendance:
                vals['attendance_status'] = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.attendance_status') or ''
                HrAttendance.write(vals)
                return HrAttendance

            return self.env['hr.attendance'].create(vals)
        attendance = self.env['hr.attendance'].search([('employee_id', '=', self.id), ('check_in', '!=', False), ('check_out', '=', False),('active', '=', True)], limit=1)
        if attendance:
            vals = {
                    'check_out': action_date,
                }
            if self.is_use_reason:
                vals['check_out_reason_categ'] = self.reason_categ.id
                vals['check_out_notes'] = self.notes_reason
            self.parse_param(vals, 'out')
            attendance.write(vals)
        else:
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
            }
            if self.active_location_ids and self.selected_active_location_id:
                vals['active_location_id'] = [(4, self.selected_active_location_id.active_location_id.id)]
                
            self.parse_param(vals)
            return self.env['hr.attendance'].create(vals)

        face_recognition_store = self.env['ir.config_parameter'].sudo(
        ).get_param('hr_attendance_face_recognition_store')
        snapshot = False
        if face_recognition_store:
            snapshot = self.env.context.get("webcam", False)
        if location:
            if self.attendance_state == "checked_in":
                attendance.write(
                    {
                        "check_in_latitude": location[0],
                        "check_in_longitude": location[1],
                        'face_recognition_access_check_in':snapshot,
                    }
                )
            else:
                attendance.write(
                    {
                        "check_out_latitude": location[0],
                        "check_out_longitude": location[1],
                        'face_recognition_access_check_out':snapshot,
                    }
                )
            if self.active_location_ids and self.selected_active_location_id:
                attendance.active_location_id = [(4, self.selected_active_location_id.active_location_id.id)]
        if self.attendance_state == 'checked_in':
            if self.is_use_reason:
                attendance.check_in_reason_categ = self.reason_categ.id
                attendance.check_in_notes = self.notes_reason
        return attendance
    
    @api.onchange('allow_offline_attendance')
    def onchange_allow_offline_attendance(self):
        for rec in self:
            if not rec.allow_offline_attendance:
                rec.auto_submit_data_record = False


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"


    def attendance_manual(self, next_action, entered_pin=None):
        self.ensure_one()
        can_check_without_pin = not self.env.user.has_group('hr_attendance.group_hr_attendance_use_pin') or (self.user_id == self.env.user and entered_pin is None)
        face_recognition_kiosk_auto = self.env['ir.config_parameter'].sudo().get_param('hr_attendance_face_recognition_kiosk_auto')
        if face_recognition_kiosk_auto:
            return self._attendance_action(next_action)
        elif can_check_without_pin or entered_pin is not None and entered_pin == self.sudo().pin:
            return self._attendance_action(next_action)

        return {'warning': _('Wrong PIN')}