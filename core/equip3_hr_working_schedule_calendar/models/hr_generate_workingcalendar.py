from odoo import api, fields, models, _
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from datetime import timedelta, datetime
import calendar
from odoo.exceptions import ValidationError
import time
from pytz import timezone, UTC, utc
import pytz


class HrGenerateWorkingCalendar(models.Model):
    _name = 'hr.generate.workingcalendar'
    _description = "Generate Working Calendar"
    _order = 'id desc'

    # @api.model
    # def _company_employee_domain(self):
    #     return [('company_id','=', self.env.company.id)]

    generate_type = fields.Selection([('create_update', 'Create/Update working calendar'),
                                      ('clear', 'Clear working calendar'),
                                      ('update', 'Update working calendar with other working hours')
                                      ], string='Generate Type', states={'generated': [('readonly', True)]},
                                     required=True, default="create_update")
    schedule_type = fields.Selection([('fixed_schedule', 'Fixed Schedule'),
                                      ('shift_pattern', 'Shift Schedule'),
                                      ('roster_schedule', 'Roster Schedule'),
                                      ], states={'generated': [('readonly', True)]}, string='Schedule Type')
    follow_contract_period = fields.Boolean('Follow Contract Period', default=True,
                                            states={'generated': [('readonly', True)]})
    date = fields.Date('Date', default=fields.Date.today(), states={'generated': [('readonly', True)]})
    start_date = fields.Date('Start Date', default=time.strftime('%Y-01-01'),
                             states={'generated': [('readonly', True)]})
    end_date = fields.Date('End Date', default=time.strftime('%Y-12-31'), states={'generated': [('readonly', True)]})
    past_record = fields.Char('Record', default='User cannot delete for past dated employee working schedule record')
    is_past_date = fields.Boolean('Past Date', compute='compute_current_date')
    state = fields.Selection([('draft', 'Draft'), ('generated', 'Generated')], string="State", default='draft')
    resource_calendar_id = fields.Many2one('resource.calendar', string="Working Schedule",
                                           states={'generated': [('readonly', True)]})
    employee_ids = fields.Many2many('hr.employee', string="Employee", states={'generated': [('readonly', True)]})

    @api.onchange('generate_type')
    def onchange_employee(self):
        res = {}
        cotract_obj = self.env['hr.contract'].search([('state', '=', 'open')])
        employee_obj = self.env['hr.employee'].search(
            [('contract_ids', '!=', False), ('contract_ids', 'in', cotract_obj.ids),('company_id','=',self.env.company.id)])
        employee_working_calendar = self.env['employee.working.schedule.calendar'].search([('employee_id.company_id','=',self.env.company.id)])
        if self.generate_type != 'create_update':
            employee_list = []
            for vals in employee_working_calendar:
                employee_list.append(vals.employee_id.id)
            res['domain'] = {'employee_ids': [('id', 'in', employee_list)]}
        elif self.generate_type == 'create_update' and employee_obj:
            employee_list = []
            for vals in employee_obj:
                employee_list.append(vals.id)
            res['domain'] = {'employee_ids': [('id', 'in', employee_list)]}
        else:
            res['domain'] = {'employee_ids': [('id', 'in', [-1])]}
        if self.generate_type == 'update':
            self.follow_contract_period = False
        else:
            self.follow_contract_period = True
        return res

    @api.depends('start_date', 'follow_contract_period', 'generate_type')
    def compute_current_date(self):
        for rec in self:
            if rec.generate_type != 'create_update' and rec.follow_contract_period == False and rec.start_date and rec.start_date < date.today():
                rec.is_past_date = True
            else:
                rec.is_past_date = False

    def clear_working_schedule(self):
        if self.generate_type == 'clear':
            if not self.is_past_date:
                for employee in self.employee_ids:
                    if self.follow_contract_period:
                        start_date = date.today()
                        end_date = employee.contract_id.date_end
                        if not employee.contract_id.date_end:
                            current_year = date.today().year
                            end_date = date(current_year, 12, 31)
                    else:
                        start_date = self.start_date
                        end_date = self.end_date
                    query_start_date = "'" + str(start_date) + "'"
                    query_end_date = "'" + str(end_date) + "'"
                    self.env.cr.execute("""delete from
                                                employee_working_schedule_calendar where employee_id=%d and date_start between 
                                                %s and %s""" % (
                        employee, query_start_date, query_end_date))
            else:
                raise ValidationError(
                    _("User cannot Update and delete for past dated employee working schedule record"))

    def action_generate(self):
        if self.generate_type == 'clear':
            self.clear_working_schedule()
        else:
            if self.is_past_date:
                raise ValidationError(
                    _("User cannot Update and delete for past dated employee working schedule record"))
            for rec in self:
                for employee in rec.employee_ids:
                    contract = employee.contract_id
                    if self.generate_type == 'update':
                        resource = self.resource_calendar_id
                    else:
                        resource = employee.contract_id.resource_calendar_id
                    holiday_list = []
                    weekend_list = []
                    if rec.follow_contract_period:
                        current_year = date.today().year
                        start_date = date(current_year, 1, 1)
                        end_date = contract.date_end
                        if contract.date_start >= start_date:
                            start_date = contract.date_start
                        if not contract.date_end:
                            end_date = date(current_year, 12, 31)
                        if self.generate_type == 'update':
                            start_date = date.today()
                    else:
                        end_date = rec.end_date
                        if rec.start_date >= contract.date_start:
                            start_date = rec.start_date
                        else:
                            start_date = contract.date_start
                    if not resource.allow_public_holidays:
                        weekend_start_date = start_date
                        weekend_end_date = end_date
                        while weekend_start_date <= weekend_end_date:
                            if weekend_start_date.weekday() in (5, 6):
                                weekend_list.append(weekend_start_date)
                            weekend_start_date += relativedelta(days=1)
                        for holiday in resource.global_leave_ids:
                            holiday_start_date = holiday.date_from
                            holiday_end_date = holiday.date_to
                            while holiday_start_date <= holiday_end_date:
                                holiday_list.append(holiday_start_date)
                                holiday_start_date += relativedelta(days=1)
                    if start_date and end_date:
                        query_start_date = "'" + str(start_date) + "'"
                        query_end_date = "'" + str(end_date) + "'"
                        self.env.cr.execute("""delete from
                            employee_working_schedule_calendar where employee_id=%d and date_start between 
                            %s and %s""" % (
                            employee.id, query_start_date, query_end_date))
                        while start_date <= end_date:
                            if resource.schedule == 'fixed_schedule':
                                if start_date not in holiday_list and start_date not in weekend_list:
                                    for attendance in resource.attendance_ids:
                                        if str(start_date.weekday()) in attendance.dayofweek:
                                            query_start_date = "'" + str(start_date) + "'"
                                            query_end_date = "'" + str(end_date) + "'"

                                            start_time = timedelta(hours=attendance.hour_from)
                                            start_str1 = str(start_time)
                                            start_str2 = start_str1[:-3]
                                            start_date_time = str(start_date) + ' ' + str(start_time)
                                            start_tz = datetime.strptime(start_date_time, '%Y-%m-%d %H:%M:%S')
                                            checkin = fields.Datetime.to_string(pytz.timezone(resource.tz).localize(fields.Datetime.from_string(start_tz),is_dst=None).astimezone(pytz.utc))
                                            query_checkin = "'" + str(checkin) + "'"

                                            start_checkin_time = timedelta(hours=attendance.start_checkin)
                                            start_date_checkin_time = str(start_date) + ' ' + str(start_checkin_time)
                                            start_checkin_tz = datetime.strptime(start_date_checkin_time, '%Y-%m-%d %H:%M:%S')
                                            start_checkin = fields.Datetime.to_string(pytz.timezone(resource.tz).localize(fields.Datetime.from_string(start_checkin_tz),is_dst=None).astimezone(pytz.utc))
                                            query_start_checkin = "'" + str(start_checkin) + "'"

                                            if resource.hr_overlaps_schema:
                                                if attendance.hour_to < attendance.hour_from:
                                                    date_end = start_date + timedelta(days=1)
                                                else:
                                                    date_end = start_date
                                                date_end_checkout = start_date + timedelta(days=1)
                                            else:
                                                if attendance.hour_to < attendance.hour_from:
                                                    date_end = start_date + timedelta(days=1)
                                                    date_end_checkout = start_date + timedelta(days=1)
                                                else:
                                                    date_end = start_date
                                                    date_end_checkout = start_date

                                            end_time = timedelta(hours=attendance.hour_to)
                                            end_str1 = str(end_time)
                                            end_str2 = end_str1[:-3]
                                            end_date_time = str(date_end) + ' ' + str(end_time)
                                            end_tz = datetime.strptime(end_date_time, '%Y-%m-%d %H:%M:%S')
                                            checkout = fields.Datetime.to_string(pytz.timezone(resource.tz).localize(fields.Datetime.from_string(end_tz),is_dst=None).astimezone(pytz.utc))
                                            query_checkout = "'" + str(checkout) + "'"

                                            end_checkout_time = timedelta(hours=attendance.end_checkout)
                                            end_date_checkout_time = str(date_end_checkout) + ' ' + str(end_checkout_time)
                                            end_checkout_tz = datetime.strptime(end_date_checkout_time, '%Y-%m-%d %H:%M:%S')
                                            end_checkout = fields.Datetime.to_string(pytz.timezone(resource.tz).localize(fields.Datetime.from_string(end_checkout_tz),is_dst=None).astimezone(pytz.utc))
                                            query_end_checkout = "'" + str(end_checkout) + "'"
                                            
                                            if employee.department_id.id:
                                                department = employee.department_id.id
                                                active = True
                                                attendance_formula_id = "NULL"
                                                if attendance.attendance_formula_id:
                                                    attendance_formula_id = attendance.attendance_formula_id.id
                                                self.env.cr.execute("""INSERT
                                                INTO
                                                employee_working_schedule_calendar(
                                                employee_id, contract_id, department_id, working_hours, dayofweek, date_start, 
                                                date_end, hour_from, hour_to, tolerance_late, break_from, break_to, minimum_hours, active, checkin, checkout,
                                                start_checkin, end_checkout, attendance_formula_id
                                                )
                                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""" % (
                                                    employee.id, contract.id, department, resource.id,
                                                    attendance.dayofweek, query_start_date, query_end_date,
                                                    attendance.hour_from,
                                                    attendance.hour_to, attendance.grace_time_for_late,
                                                    attendance.break_from,
                                                    attendance.break_to,
                                                    attendance.minimum_hours, active, query_checkin, query_checkout,
                                                    query_start_checkin, query_end_checkout,
                                                    attendance_formula_id))
                            elif resource.schedule == 'shift_pattern':
                                last_working = self.env['calendar.working.times'].search([('resource_calendar_id','=',resource.id)], order='id desc', limit=1)[0]
                                date_end = last_working.working_date
                                if date_end > end_date:
                                    date_end = end_date
                                for working in resource.calendar_working_time_ids:
                                    if start_date not in holiday_list and start_date == working.working_date:
                                        query_start_date = "'" + str(start_date) + "'"
                                        query_end_date = "'" + str(date_end) + "'"

                                        start_time = timedelta(hours=working.start_time)
                                        start_str1 = str(start_time)
                                        start_str2 = start_str1[:-3]
                                        start_date_time = str(start_date) + ' ' + str(start_time)
                                        start_tz = datetime.strptime(start_date_time, '%Y-%m-%d %H:%M:%S')
                                        checkin = fields.Datetime.to_string(pytz.timezone(resource.tz).localize(fields.Datetime.from_string(start_tz),is_dst=None).astimezone(pytz.utc))
                                        query_checkin = "'" + str(checkin) + "'"

                                        start_checkin_time = timedelta(hours=working.start_checkin)
                                        start_date_checkin_time = str(start_date) + ' ' + str(start_checkin_time)
                                        start_checkin_tz = datetime.strptime(start_date_checkin_time, '%Y-%m-%d %H:%M:%S')
                                        start_checkin = fields.Datetime.to_string(pytz.timezone(resource.tz).localize(fields.Datetime.from_string(start_checkin_tz),is_dst=None).astimezone(pytz.utc))
                                        query_start_checkin = "'" + str(start_checkin) + "'"

                                        if resource.hr_overlaps_schema:
                                            if working.end_time < working.start_time:
                                                date_end = start_date + timedelta(days=1)
                                            else:
                                                date_end = start_date
                                            date_end_checkout = start_date + timedelta(days=1)
                                        else:
                                            if working.end_time < working.start_time:
                                                date_end = start_date + timedelta(days=1)
                                                date_end_checkout = start_date + timedelta(days=1)
                                            else:
                                                date_end = start_date
                                                date_end_checkout = start_date

                                        end_time = timedelta(hours=working.end_time)
                                        end_str1 = str(end_time)
                                        end_str2 = end_str1[:-3]
                                        end_date_time = str(date_end) + ' ' + str(end_time)
                                        end_tz = datetime.strptime(end_date_time, '%Y-%m-%d %H:%M:%S')
                                        checkout = fields.Datetime.to_string(pytz.timezone(resource.tz).localize(fields.Datetime.from_string(end_tz),is_dst=None).astimezone(pytz.utc))
                                        query_checkout = "'" + str(checkout) + "'"

                                        end_checkout_time = timedelta(hours=working.end_checkout)
                                        end_date_checkout_time = str(date_end_checkout) + ' ' + str(end_checkout_time)
                                        end_checkout_tz = datetime.strptime(end_date_checkout_time, '%Y-%m-%d %H:%M:%S')
                                        end_checkout = fields.Datetime.to_string(pytz.timezone(resource.tz).localize(fields.Datetime.from_string(end_checkout_tz),is_dst=None).astimezone(pytz.utc))
                                        query_end_checkout = "'" + str(end_checkout) + "'"
                                        
                                        if employee.department_id.id:
                                            department = employee.department_id.id
                                            active = True
                                            dayofweek = start_date.weekday()
                                            day_type = "'" + working.shifting_id.day_type + "'"
                                            attendance_formula_id = "NULL"
                                            if working.attendance_formula_id:
                                                attendance_formula_id = working.attendance_formula_id.id
                                            self.env.cr.execute("""INSERT
                                            INTO
                                            employee_working_schedule_calendar(
                                            employee_id, contract_id, department_id, working_hours, dayofweek, date_start, 
                                            date_end, hour_from, hour_to, tolerance_late, break_from, break_to, minimum_hours, 
                                            active, checkin, checkout, day_type, start_checkin, end_checkout, attendance_formula_id
                                            )
                                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""" % (
                                                employee.id, contract.id, department, resource.id,
                                                dayofweek, query_start_date, query_end_date,
                                                working.start_time,
                                                working.end_time, working.grace_time_for_late,
                                                working.break_from,
                                                working.break_to,
                                                working.minimum_hours,
                                                active, query_checkin, query_checkout, day_type,
                                                query_start_checkin, query_end_checkout,
                                                attendance_formula_id))
                                            # working_calendar_id = self.env.cr.fetchone()[0]
                                            # if working.is_overnight:
                                            #     no_checkout_time = timedelta(hours=working.no_checkout)
                                            #     no_checkout_date_time = str(date_end) + ' ' + str(no_checkout_time)
                                            #     no_checkout_tz = datetime.strptime(no_checkout_date_time, '%Y-%m-%d %H:%M:%S')
                                            #     no_checkout = fields.Datetime.to_string(pytz.timezone(self.env.context.get('tz', 'utc') or 'utc').localize(fields.Datetime.from_string(no_checkout_tz),is_dst=None).astimezone(pytz.utc))
                                            #     # query_no_checkout = "'" + str(no_checkout) + "'"
                                            #     calendar_obj = self.env['employee.working.schedule.calendar'].browse(working_calendar_id)
                                            #     calendar_obj.no_checkout_time = str(no_checkout)

                            start_date += relativedelta(days=1)
                leaves = self.env['resource.calendar.leaves'].search([('resource_id', '=', False)])
                for holiday in leaves:
                    start_holiday = holiday.date_from
                    end_holiday = holiday.date_to
                    while start_holiday <= end_holiday:
                        leaves_exist = self.env['employee.working.schedule.calendar'].search(
                            [('date_start', '=', start_holiday), ('is_holiday', '=', True)])
                        if not leaves_exist:
                            self.env['employee.working.schedule.calendar'].create({
                                'employee_id': False,
                                'contract_id': False,
                                'department_id': False,
                                'working_hours': False,
                                'dayofweek': str(start_holiday.weekday()),
                                'date_start': start_holiday,
                                'date_end': start_holiday,
                                'hour_from': 0.01,
                                'hour_to': 23.99,
                                'is_holiday': True,
                                'holiday_remark': holiday.name,
                            })
                        start_holiday += relativedelta(days=1)
        self.state = 'generated'
