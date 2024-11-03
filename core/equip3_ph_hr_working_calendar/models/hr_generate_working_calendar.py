from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import time
from dateutil.rrule import rrule, DAILY
import pytz


class HrGenerateWorkingCalendar(models.Model):
    _name = "hr.generate.working.calendar"
    _description = "Generate Working Calendar"

    start_date = fields.Date(
        "Start Date",
        default=time.strftime("%Y-01-01"),
        states={"generated": [("readonly", True)]},
    )
    end_date = fields.Date(
        "End Date",
        default=time.strftime("%Y-12-31"),
        states={"generated": [("readonly", True)]},
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("generated", "Generated")],
        string="State",
        default="draft",
    )
    employee_ids = fields.Many2many("hr.employee", string="Employee")

    def name_get(self):
        result = []
        for record in self:
            name = "Draft(%s)" % (record.id)
            if record.start_date and record.end_date:
                name = "Period of %s-%s" % (record.start_date, record.end_date)
            result += [(record.id, name)]
        return result

    def action_generate(self):
        user_tz = pytz.timezone(self.env.user.tz)
        utc_tz = pytz.utc

        for calendar in self:
            start_date = fields.Date.from_string(calendar.start_date)
            end_date = fields.Date.from_string(calendar.end_date)
            dates = rrule(DAILY, dtstart=start_date, until=end_date)

            if not calendar.employee_ids:
                continue

            for employee in calendar.employee_ids:
                if not employee.resource_calendar_id:
                    raise UserError(_("Employee %s does not have a resource calendar") % employee.name)

                if employee.resource_calendar_id.schedule == "fixed_schedule":
                    calendar.create_fix_schedule_working_calendar(employee, dates, user_tz, utc_tz)

                elif employee.resource_calendar_id.schedule == "shift_pattern":
                    calendar.create_shift_schedule_working_calendar(employee, dates, user_tz, utc_tz)

            calendar.state = "generated"
    
    def create_fix_schedule_working_calendar(self, employee, dates, user_tz, utc_tz):
        employee_working_calendar_obj = self.env["hr.employee.working.calendar"]
        for attendance in employee.resource_calendar_id.attendance_ids:
            hour_from, hour_to = attendance.hour_from, attendance.hour_to

            for date in dates:
                if str(date.weekday()) != attendance.dayofweek:  # Skip Sundays
                    continue

                # Check if a record already exists
                if employee_working_calendar_obj.search_count([
                    ("employee_id", "=", employee.id),
                    ("date_start", "=", date.date()),
                    ("hour_from", "=", hour_from),
                    ("hour_to", "=", hour_to),
                ]):
                    continue

                start_time = datetime.combine(date.date(), datetime.min.time()) + timedelta(hours=hour_from)
                end_time = datetime.combine(date.date(), datetime.min.time()) + timedelta(hours=hour_to)

                # Convert to user timezone, then to UTC
                checkin = user_tz.localize(start_time).astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')
                checkout = user_tz.localize(end_time).astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')

                data = {
                    "employee_id": employee.id,
                    "contract_id": employee.contract_id.id,
                    "department_id": employee.department_id.id,
                    "working_hours": employee.resource_calendar_id.id,
                    "day_of_week": str(date.weekday()),
                    "date_start": date.date(),
                    "date_end": date.date(),
                    "hour_from": hour_from,
                    "hour_to": hour_to,
                    "tolerance_late": attendance.tolerance_for_late,
                    "break_from": attendance.break_from,
                    "break_to": attendance.break_to,
                    "minimum_hours": attendance.minimum_hours,
                    "checkin": checkin,
                    "checkout": checkout,
                    "is_generated": True,
                    "maximum_break": attendance.maximum_break,
                }

                for public_holiday in employee.resource_calendar_id.global_leave_ids:
                    local_start_datetime = public_holiday.date_from.astimezone(user_tz)
                    local_end_datetime = public_holiday.date_to.astimezone(user_tz)

                    start_date = local_start_datetime.date()
                    end_date = local_end_datetime.date()
                    
                    if date.date() >= start_date and date.date() <= end_date:
                        data["day_type"] = "public_holiday"

                employee_working_calendar_obj.create(data)


    def create_shift_schedule_working_calendar(self, employee, dates, user_tz, utc_tz):
        employee_working_calendar_obj = self.env["hr.employee.working.calendar"]
        for attendance in employee.resource_calendar_id.calendar_working_time_ids:
            work_from, work_to = attendance.work_from, attendance.work_to

            if attendance.working_date in [date.date() for date in dates]:
                # Check if a record already exists
                if employee_working_calendar_obj.search_count([
                    ("employee_id", "=", employee.id),
                    ("date_start", "=", attendance.working_date),
                    ("hour_from", "=", work_from),
                    ("hour_to", "=", work_to),
                ]):
                    continue

                start_time = datetime.combine(attendance.working_date, datetime.min.time()) + timedelta(hours=work_from)
                end_time = datetime.combine(attendance.working_date, datetime.min.time()) + timedelta(hours=work_to)

                # Convert to user timezone, then to UTC
                checkin = user_tz.localize(start_time).astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')
                checkout = user_tz.localize(end_time).astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')

                data = {
                    "employee_id": employee.id,
                    "contract_id": employee.contract_id.id,
                    "department_id": employee.department_id.id,
                    "working_hours": employee.resource_calendar_id.id,
                    "day_of_week": str(attendance.working_date.weekday()),
                    "date_start": attendance.working_date,
                    "date_end": attendance.working_date,
                    "hour_from": work_from,
                    "hour_to": work_to,
                    "tolerance_late": attendance.tolerance_for_late,
                    "break_from": attendance.break_from,
                    "break_to": attendance.break_to,
                    "minimum_hours": attendance.minimum_hours,
                    "checkin": checkin,
                    "checkout": checkout,
                    "is_generated": True,
                    "maximum_break": attendance.maximum_break,
                    "day_type": attendance.shifting_id.day_type,
                }


                for public_holiday in employee.resource_calendar_id.global_leave_ids:
                    local_start_datetime = public_holiday.date_from.astimezone(user_tz)
                    local_end_datetime = public_holiday.date_to.astimezone(user_tz)
                    
                    start_date = local_start_datetime.date()
                    end_date = local_end_datetime.date()

                    if attendance.working_date >= start_date and attendance.working_date <= end_date:
                        data["day_type"] = "public_holiday"

                employee_working_calendar_obj.create(data)
