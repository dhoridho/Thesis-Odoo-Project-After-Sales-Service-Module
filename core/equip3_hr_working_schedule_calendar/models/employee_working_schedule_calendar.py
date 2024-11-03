from odoo import api, fields, models, _
import datetime
from datetime import datetime, timedelta
from pytz import timezone, UTC, utc
import pytz
from dateutil.relativedelta import relativedelta


class EmployeeWorkingScheduleCalendar(models.Model):
    _name = 'employee.working.schedule.calendar'
    _description = "Calendar to display employees working schedule"
    _order = 'employee_id'

    WEEKDAYS = [
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ]

    name = fields.Char(string='Name', size=256, required=0, compute='get_break_from_and_to')
    user_id = fields.Many2one('res.users', string='User')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    contract_id = fields.Many2one('hr.contract', string="Contract")
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    hour_from = fields.Float(string='Work From', required=0)
    hour_to = fields.Float(string='Work To', required=0)
    dayofweek = fields.Selection(WEEKDAYS, string='Name of Day', required=0)
    working_hours = fields.Many2one('resource.calendar', string='Working Schedule')
    department_id = fields.Many2one('hr.department', string='Department')
    active = fields.Boolean('Active', default=True)
    schedule = fields.Selection(related='working_hours.schedule', string='Schedule')
    checkin = fields.Datetime('Start Working Times')
    checkout = fields.Datetime('End Working Times')
    total_working_time = fields.Char('Total Working Time')
    break_from = fields.Float('Break From')
    break_to = fields.Float('Break To')
    tolerance_late = fields.Float('Tolerance for Late')
    attendance_formula_id = fields.Many2one('hr.attendance.formula', string="Attendance Formula")
    state = fields.Selection(string="Status",
                             selection=[('checked_in', "Checked In"), ('not_checked_in', "Not Checked in")])
    date_working = fields.Date(string='Working Date')
    is_holiday = fields.Boolean(string='Is Holiday', default=False)
    holiday_remark = fields.Char(string='Holiday Remark')
    minimum_hours = fields.Float('Minimum Hours')
    day_type = fields.Selection([('work_day', 'Work Day'),
                                ('day_off', 'Day Off')
                                ], string='Day Type', default="")
    start_checkin = fields.Datetime('Start Checkin Times')
    end_checkout = fields.Datetime('End Checkout Times')
    is_import = fields.Boolean(string='Is Import', default=False)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeWorkingScheduleCalendar, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeWorkingScheduleCalendar, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.onchange('employee_id')
    def onchange_department(self):
        self.contract_id = self.employee_id.contract_id.id
        self.department_id = self.employee_id.department_id.id
        self.working_hours = self.employee_id.resource_calendar_id.id

    def get_break_from_and_to(self):
        for rec in self:
            start_str2 = 0
            if rec.date_start:
                start_date = rec.date_start
                start_time = timedelta(hours=rec.hour_from)
                start_str1 = str(start_time)
                start_str2 = start_str1[:-3]
            end_str2 = 0
            if rec.date_end:
                if rec.hour_to < rec.hour_from:
                    end_date = rec.date_start + timedelta(days=1)
                else:
                    end_date = rec.date_start
                end_time = timedelta(hours=rec.hour_to)
                end_str1 = str(end_time)
                end_str2 = end_str1[:-3]
            if rec.is_holiday and rec.holiday_remark:
                rec.name = 'Public Holidays : ' + rec.holiday_remark
            elif not rec.is_holiday and rec.employee_id:
                if rec.day_type == 'day_off':
                    rec.name = rec.employee_id.name + ' ' + 'Day Off'
                else:
                    rec.name = rec.employee_id.name + ' ' + start_str2 + ' - ' + end_str2
            else:
                rec.name = False


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)


class CalendarEmployee(models.Model):
    _name = 'calendar.employee'
    _description = 'Calendar Employee'

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('user_id_employee_id_unique', 'UNIQUE(user_id, employee_id)', 'A user cannot have the same Employee twice.')
    ]

    @api.model
    def unlink_from_employee_id(self, employee_id):
        return self.search([('employee_id', '=', partner_id)]).unlink()
