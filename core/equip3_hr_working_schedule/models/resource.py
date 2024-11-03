from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import numpy as np
from pytz import utc

WEEKDAYS = [
    ('0', 'Monday'),
    ('1', 'Tuesday'),
    ('2', 'Wednesday'),
    ('3', 'Thursday'),
    ('4', 'Friday'),
    ('5', 'Saturday'),
    ('6', 'Sunday'),
]


class resource_calendar(models.Model):
    _name = 'resource.calendar'
    _inherit = ['resource.calendar', 'mail.thread']

    @api.model
    def default_get(self, fields):
        res = super(resource_calendar, self).default_get(fields)
        for line in self.attendance_ids:
            line.unlink()
        return res

    schedule = fields.Selection([('fixed_schedule', 'Fixed Schedule'),
                                 ('shift_pattern', 'Shift Schedule'),
                                 ], string='Schedule Type', default='fixed_schedule', tracking=True)
    week_working_day = fields.Integer(string='Number Of Working', tracking=True)
    allow_public_holidays = fields.Boolean('Allow Schedule on Public Holidays')
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]",
                                tracking=True)
    schedule_period_from = fields.Date(string="Start Period")
    schedule_period_to = fields.Date(string="End Period")
    start_from_day_no = fields.Integer(string="Day Start", default=1)
    shift_variation_line_ids = fields.One2many('working.shift.variation.line', 'resource_calendar_id', 'Shift Variations')
    calendar_working_time_ids = fields.One2many('calendar.working.times', 'resource_calendar_id', 'Calendar Working Times')
    state = fields.Selection([('draft', 'Draft'),
                            ('generated', 'Generated'),
                            ], string='status', default='draft')
    break_time_to_work_hour = fields.Boolean('Calculate Break Time to Work Hour')
    hr_overlaps_schema = fields.Boolean('Overlaps Schema')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(resource_calendar, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(resource_calendar, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.onchange("start_from_day_no")
    def _onchange_start_from_day_no(self):
        for rec in self:
            if rec.start_from_day_no < 1:
                rec.start_from_day_no = 1

    def mass_update_fixed(self):
        action = self.env.ref('equip3_hr_working_schedule.action_mass_update_fixed').read()[0]
        return action
    
    @api.constrains('shift_variation_line_ids')
    def _check_total_day_shift(self):
        for rec in self:
            for line in rec.shift_variation_line_ids:
                if line.total_days < 1:
                    raise ValidationError(_("""Total Days must be grather than 0."""))

    @api.constrains('attendance_ids')
    def _check_attendance(self):
        # Avoid superimpose in attendance
        for calendar in self:
            attendance_ids = calendar.attendance_ids.filtered(
                lambda attendance: not attendance.resource_id and attendance.display_type is False)
            if calendar.two_weeks_calendar:
                calendar._check_overlap(attendance_ids.filtered(lambda attendance: attendance.week_type == '0'))
                calendar._check_overlap(attendance_ids.filtered(lambda attendance: attendance.week_type == '1'))

    @api.onchange('schedule_period_from', 'schedule_period_to')
    def _onchange_date(self):
        for record in self:
            if record.schedule_period_from and record.schedule_period_to:
                if record.schedule_period_from > record.schedule_period_to:
                    raise ValidationError("Schedule period To must be greater than Schedule period from!")

    def action_generate(self):
        for rec in self:
            if not rec.schedule_period_from and not rec.schedule_period_to:
                raise ValidationError("Schedule period from and To must be filled!")
            if not rec.shift_variation_line_ids:
                raise ValidationError("You must select shifting variation(s) to generate.")
            rec._create_calendar_working_times()
            rec.state = 'generated'

    def _create_calendar_working_times(self):
        self.ensure_one()
        self.calendar_working_time_ids.unlink()
        obj_calendar = self.env["calendar.working.times"]
        start_date = self.schedule_period_from
        ends_date = self.schedule_period_to
        diff = abs((ends_date - start_date).days + 1)
        start_from_day_no = self.start_from_day_no
        variations = self.shift_variation_line_ids
        diffs = 1
        nums = 1
        num_var = []
        while diffs <= diff + (start_from_day_no - 1):
            num = 1
            for variation in variations:
                i = 1
                while i <= variation.total_days:
                    if nums >= start_from_day_no:
                        num_var += [variation]
                    if (nums == diff + (start_from_day_no - 1)):
                        break
                    i += 1
                    num += 1
                    nums += 1
            if (nums >= diff + (start_from_day_no - 1)):
                break
            diffs += 1

        tgl_range = []
        while start_date <= ends_date:
            tgl_range += [start_date]
            start_date = start_date + relativedelta(days=+1)

        tgl_array = np.array(tgl_range)

        list_calendar = {}
        for A, B in zip(tgl_array, num_var):
            list_calendar[A] = B

        for key, val in list_calendar.items():
            attendance_formula_id = False
            if val.attendance_formula_id:
                attendance_formula_id = val.attendance_formula_id.id
            obj_calendar.create({
                "working_date": key,
                "shifting_id": val.shifting_id.id,
                "resource_calendar_id": self.id,
                "attendance_formula_id": attendance_formula_id,
            })

    def get_shift_work_days_data(self, from_datetime, to_datetime):
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=utc)

        from_full = from_datetime - timedelta(days=0)
        to_full = to_datetime + timedelta(days=0)

        date_from = from_full.date()
        date_to = to_full.date()

        working_days = self.calendar_working_time_ids.filtered(
                    lambda r: r.working_date >= date_from and r.working_date <= date_to and r.shifting_id.day_type == "work_day"
                )
        days = len(working_days)
        hours = sum(working_days.mapped("minimum_hours")) or 0.0
        return {
            'days': days,
            'hours': hours,
        }

class resource_calendar_attendance_in(models.Model):
    _inherit = 'resource.calendar.attendance'

    name = fields.Char('Name', compute="fetch_sl_no")
    grace_time_for_late = fields.Float('Tolerance for Late')
    attendance_formula_id = fields.Many2one('hr.attendance.formula', string="Attendance Formula")
    break_from = fields.Float('Break From')
    break_to = fields.Float('Break To')
    half_day = fields.Boolean('Allow Half Day')
    minimum_hours = fields.Float(string='Minimum Hours', required=0)
    start_checkin = fields.Float(string='Start Checkin', default=0)
    end_checkout = fields.Float(string='End Checkout', default=0)

    @api.depends('dayofweek')
    def fetch_sl_no(self):
        for line in self:
            if line.dayofweek:
                line.name = line.dayofweek

    @api.onchange('break_from')
    def onchange_break_from(self):
        for line in self:
            if line.hour_from <= line.break_from and line.hour_to >= line.break_from:
                continue
            else:
                raise ValidationError(_("""Break From must between Work From and Work To."""))
    
    @api.onchange('break_to')
    def onchange_break_from(self):
        for line in self:
            if line.hour_from <= line.break_to and line.hour_to >= line.break_to:
                continue
            else:
                raise ValidationError(_("""Break To must between Work From and Work To."""))

class WorkingShiftVariationLine(models.Model):
    _name = 'working.shift.variation.line'

    resource_calendar_id = fields.Many2one('resource.calendar', ondelete='cascade')
    schedule = fields.Selection(string='Schedule', related='resource_calendar_id.schedule')
    name = fields.Char(related='shifting_id.name', string='Name')
    sequence = fields.Integer('Sequence', compute="fetch_sl_no")
    shifting_id = fields.Many2one('hr.shift.variation', string='Shifting')
    day_type = fields.Selection(related='shifting_id.day_type', string='Day Type')
    start_time = fields.Float(related='shifting_id.work_from', string='Work From')
    end_time = fields.Float(related='shifting_id.work_to', string='Work To')
    attendance_formula_id = fields.Many2one('hr.attendance.formula', string="Attendance Formula")
    total_days = fields.Integer(string='Total Days')
    minimum_hours = fields.Float(related='shifting_id.minimum_hours', string='Minimum Hours')
    start_checkin = fields.Float(related='shifting_id.start_checkin', string='Start Checkin')
    end_checkout = fields.Float(related='shifting_id.end_checkout', string='End Checkout')

    @api.depends('resource_calendar_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.resource_calendar_id.shift_variation_line_ids:
            sl = sl + 1
            line.sequence = sl

    @api.onchange('shifting_id')
    def onchange_shifting_id(self):
        for line in self:
            if line.shifting_id.attendance_formula_id:
                line.attendance_formula_id = line.shifting_id.attendance_formula_id.id

class CalendarWorkingTimes(models.Model):
    _name = 'calendar.working.times'

    resource_calendar_id = fields.Many2one('resource.calendar', ondelete='cascade')
    name = fields.Char(related='shifting_id.name', string='Name')
    shifting_id = fields.Many2one('hr.shift.variation', string='Variation Shifting')
    working_date = fields.Date('Working Date')
    start_time = fields.Float(related='shifting_id.work_from', string='Work From')
    end_time = fields.Float(related='shifting_id.work_to', string='Work To')
    break_from = fields.Float(related='shifting_id.break_from', string='Break From')
    break_to = fields.Float(related='shifting_id.break_to', string='Break To')
    grace_time_for_late = fields.Float(related='shifting_id.tolerance_for_late', string='Tolerance for Late')
    attendance_formula_id = fields.Many2one('hr.attendance.formula', string="Attendance Formula")
    minimum_hours = fields.Float(related='shifting_id.minimum_hours', string='Minimum Hours')
    start_checkin = fields.Float(related='shifting_id.start_checkin', string='Start Checkin')
    end_checkout = fields.Float(related='shifting_id.end_checkout', string='End Checkout')