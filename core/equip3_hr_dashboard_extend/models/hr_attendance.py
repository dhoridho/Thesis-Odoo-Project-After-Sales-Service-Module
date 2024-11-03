from odoo import models, fields, api, _
from odoo.tools.misc import split_every
from datetime import date

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.model
    def cron_create_attendance_daily(self):
        EmployeeWorkingScheduleCalendar = self.env['employee.working.schedule.calendar'].sudo().search([('date_start','=',date.today())])
        for working_schedule in split_every(100, EmployeeWorkingScheduleCalendar):
            for schedule in working_schedule:
                HrAttendance = self.env['hr.attendance'].sudo().search([('employee_id','=',schedule.employee_id.id),('start_working_date','=',schedule.date_start)], limit=1)
                if not HrAttendance:
                    self.env['hr.attendance'].sudo().create({
                        'employee_id': schedule.employee_id.id,
                        'check_in': False,
                        'check_out': False,
                        'start_working_times': schedule.checkin,
                        'start_working_date': schedule.date_start,
                        'calendar_id': schedule.id,
                        'attendance_status': 'absent',
                        'is_absent': True
                    })