from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.rrule import rrule, DAILY
from datetime import timedelta
from pytz import utc


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    schedule = fields.Selection(
        selection=[
            ("fixed_schedule", "Fixed Schedule"),
            ("shift_pattern", "Shift Schedule"),
        ],
        string="Schedule Type",
        default="fixed_schedule",
        tracking=True,
    )
    schedule_period_from = fields.Date("Start Period")
    schedule_period_to = fields.Date("End Period")
    state = fields.Selection(
        selection=[("draft", "Draft"), ("generated", "Generated")],
        string="State",
        default="draft",
    )
    calendar_working_time_ids = fields.One2many(
        comodel_name="calendar.working.times",
        inverse_name="resource_calendar_id",
        string="Calendar Working Times",
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super(ResourceCalendar, self).default_get(fields_list)
        if "attendance_ids" in fields_list:
            defaults["attendance_ids"] = [(5, 0, 0)]
        return defaults

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.attendance_ids:
                line.sequence = current_sequence
                current_sequence += 1

    @api.onchange("schedule")
    def _onchange_schedule(self):
        for calendar in self:
            calendar.attendance_ids = [(5, 0, 0)]
            calendar._reset_sequence()
    
    @api.onchange('schedule_period_from', 'schedule_period_to')
    def _onchange_date(self):
        for calendar in self:
            if calendar.schedule_period_from and calendar.schedule_period_to:
                if calendar.schedule_period_from > calendar.schedule_period_to:
                    raise ValidationError(_("Schedule period To must be greater than Schedule period from!"))

    @api.constrains('attendance_ids')
    def _check_attendance(self):
        for calendar in self:
            attendance_ids = calendar.attendance_ids.filtered(
                lambda attendance: not attendance.resource_id and attendance.display_type is False)
            if calendar.two_weeks_calendar:
                calendar._check_overlap(attendance_ids.filtered(lambda attendance: attendance.week_type == '0'))
                calendar._check_overlap(attendance_ids.filtered(lambda attendance: attendance.week_type == '1'))

    def action_generate(self):
        for calendar in self:
            if not calendar.schedule_period_from and not calendar.schedule_period_to:
                raise ValidationError(_("Schedule period from and To must be filled!"))
            if not calendar.attendance_ids.filtered(lambda attendance: attendance.shifting_id != False):
                raise UserError(_("You must select shifting variation(s) to generate."))
            calendar._create_calendar_working_times()
            calendar.state = 'generated'

    def _create_calendar_working_times(self):
        self.ensure_one()
        self.calendar_working_time_ids.unlink()
        calendar_working_times_obj = self.env["calendar.working.times"]
        start_date = fields.Date.from_string(self.schedule_period_from)
        end_date = fields.Date.from_string(self.schedule_period_to)
        date_ranges = list(rrule(DAILY, dtstart=start_date, until=end_date))
        shift_variant_lines = self.attendance_ids.filtered(
            lambda attendance: attendance.shifting_id != False
        )

        shift_cycle = []
        for shift in shift_variant_lines:
            shift_cycle.extend([shift] * shift.total_days)

        # If there are more dates than total shift days, repeat the shifts to cover all dates
        while len(shift_cycle) < len(date_ranges):
            shift_cycle.extend(shift_cycle)

        # Trim the list to match the exact length of date_ranges
        shift_cycle = shift_cycle[:len(date_ranges)]

        unique_working_dates = set()
        for index, date_range in enumerate(date_ranges):
            shift = shift_cycle[index]
            
            # Check if a record is exists for this date and shift
            if calendar_working_times_obj.search_count([
                ("working_date", "=", date_range.date()),
                ("shifting_id", "=", shift.shifting_id.id),
                ("resource_calendar_id", "=", self.id),
            ]):
                continue
            
            data = {
                "working_date": date_range.date(),
                "shifting_id": shift.shifting_id.id,
                "resource_calendar_id": self.id,
            }
            is_allowed_create_calendar = (
                data["working_date"] not in unique_working_dates
            )

            if is_allowed_create_calendar:
                unique_working_dates.add(data["working_date"])
                calendar_working_times_obj.create(data)
    
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
            lambda calendar: calendar.working_date >= date_from
            and calendar.working_date <= date_to
            and calendar.shifting_id.day_type == "work_day"
        )
        days = len(working_days)
        hours = sum(working_days.mapped("minimum_hours")) or 0.0
        return {
            "days": days,
            "hours": hours,
        }


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"
    _order = "sequence"

    name = fields.Char(required=False)
    sequence = fields.Integer("Sequence")
    shifting_id = fields.Many2one("hr.shift.variation", string="Shifting")
    total_days = fields.Integer(string="Total Days")
    maximum_break = fields.Float(string="Maximum Break")

    @api.onchange("shifting_id")
    def onchange_shifting_id(self):
        hour_from = hour_to = break_from = break_to = minimum_hours = tolerance_for_late = maximum_break = 0
        for line in self:
            if line.shifting_id:
                hour_from = line.shifting_id.work_from
                hour_to = line.shifting_id.work_to
                break_from = line.shifting_id.break_from
                break_to = line.shifting_id.break_to
                minimum_hours = line.shifting_id.minimum_hours
                tolerance_for_late = line.shifting_id.tolerance_for_late
                maximum_break = line.shifting_id.maximum_break

            line.hour_from = hour_from
            line.hour_to = hour_to
            line.break_from = break_from
            line.break_to = break_to
            line.minimum_hours = minimum_hours
            line.tolerance_for_late = tolerance_for_late
            line.maximum_break = maximum_break

    @api.model
    def default_get(self, fields):
        res = super(ResourceCalendarAttendance, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if "attendance_ids" in context_keys:
                if len(self._context.get("attendance_ids")) > 0:
                    next_sequence = len(self._context.get("attendance_ids")) + 1
            res.update({"sequence": next_sequence})
        return res

    def unlink(self):
        approval = self.calendar_id
        res = super(ResourceCalendarAttendance, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ResourceCalendarAttendance, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.calendar_id._reset_sequence()
        return res
