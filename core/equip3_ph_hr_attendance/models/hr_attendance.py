from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import pytz


class HrAttendanceInherit(models.Model):
    _inherit = "hr.attendance"

    working_schedule_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Working Schedule",
        compute="_compute_working_schedule",
        store=True,
    )
    start_working_date = fields.Date(
        string="Working Date", default=fields.Date.today(), required=True
    )
    hour_from = fields.Float(
        string="Work From", compute="_compute_working_schedule", store=True
    )
    hour_to = fields.Float(
        string="Work To", compute="_compute_working_schedule", store=True
    )
    tolerance_late = fields.Float(
        "Tolerance for Late", compute="_compute_working_schedule", store=True
    )
    break_from = fields.Float(
        "Allowed Start Break", compute="_compute_working_schedule", store=True
    )
    break_to = fields.Float("Allowed End Break", compute="_compute_working_schedule", store=True)
    minimum_hours = fields.Float(
        "Minimum Hours", compute="_compute_working_schedule", store=True
    )
    check_in_status = fields.Selection(
        selection=[("on_time", "On Time"), ("late", "Late")],
        string="Check In Status",
        compute="_compute_check_in_status",
        store=True,
    )
    check_out_status = fields.Selection(
        selection=[
            ("on_time", "On Time"),
            ("late", "Late"),
            ("not_fulfill", "Not Fulfill"),
        ],
        string="Check Out Status",
        compute="_compute_check_out_status",
    )
    attendance_status = fields.Selection(
        selection=[("present", "Present"), ("absent", "Absent")],
        string="Attendance Status",
        compute="_compute_attendance_status",
        store=True,
    )
    worked_hours = fields.Float(
        string="worked_hours", compute="_compute_worked_hours", store=True
    )
    check_out_difference = fields.Float(
        string="Check Out Difference",
        compute="_compute_attendance_status",
        store=True
    )
    start_break = fields.Datetime(string="Start Break")
    end_break = fields.Datetime(string="End Break")
    maximum_break = fields.Float(
        string="Maximum Break", compute="_compute_working_schedule", store=True
    )
    total_break = fields.Float(
        string="Total Break", compute="_compute_total_break", store=True
    )
    total_over_break = fields.Float(
        string="Total Over Break", compute="_compute_total_break", store=True
    )

    day_maps = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    def set_working_schedule_values(self, working_schedule, working_date, day_index):
        if working_schedule.schedule == "fixed_schedule":
            for schedule in working_schedule.attendance_ids:
                if schedule.dayofweek == day_index:
                    self.hour_from = schedule.hour_from
                    self.hour_to = schedule.hour_to
                    self.tolerance_late = schedule.tolerance_for_late
                    self.break_from = schedule.break_from
                    self.break_to = schedule.break_to
                    self.minimum_hours = schedule.minimum_hours
                    self.maximum_break = schedule.maximum_break
        else:
            for schedule in working_schedule.calendar_working_time_ids:
                if schedule.working_date == working_date:
                    self.hour_from = schedule.work_from
                    self.hour_to = schedule.work_to
                    self.tolerance_late = schedule.tolerance_for_late
                    self.break_from = schedule.break_from
                    self.break_to = schedule.break_to
                    self.minimum_hours = schedule.minimum_hours
                    self.maximum_break = schedule.maximum_break
        

    def reset_working_schedule_values(self):
        for attendance in self:
            attendance.working_schedule_id = False
            attendance.hour_from = 0.0
            attendance.hour_to = 0.0
            attendance.tolerance_late = 0.0
            attendance.break_from = 0.0
            attendance.break_to = 0.0
            attendance.minimum_hours = 0.0
            attendance.maximum_break = 0.0

    @api.depends("employee_id", "working_schedule_id", "check_in")
    def _compute_check_in_status(self):
        for attendance in self:
            if (
                attendance.hour_from
                and attendance.tolerance_late
                and attendance.check_in
            ):
                max_check_in = attendance.hour_from + attendance.tolerance_late
                expected_time = datetime.combine(
                    attendance.start_working_date, datetime.min.time()
                ) + timedelta(hours=max_check_in)

                user_tz = self.env.user.tz or "UTC"
                local_tz = pytz.timezone(user_tz)
                expected_time = local_tz.localize(expected_time)

                # Convert check_in to the user's local timezone
                check_in_utc = fields.Datetime.from_string(attendance.check_in)
                check_in_local = pytz.utc.localize(check_in_utc).astimezone(local_tz)

                if check_in_local <= expected_time:
                    attendance.check_in_status = "on_time"
                else:
                    attendance.check_in_status = "late"
            else:
                attendance.check_in_status = False

    @api.depends("employee_id", "working_schedule_id", "check_in", "check_out")
    def _compute_check_out_status(self):
        for attendance in self:
            if (
                attendance.hour_from
                and attendance.tolerance_late
                and attendance.check_in
                and attendance.check_out
            ):
                allowed_check_out = (
                    attendance.break_to - attendance.break_from
                ) + attendance.minimum_hours
                check_out_difference = allowed_check_out - attendance.worked_hours
                attendance.check_out_difference = check_out_difference
                if attendance.worked_hours >= allowed_check_out:
                    attendance.check_out_status = "on_time"
                else:
                    attendance.check_out_status = "not_fulfill"
            else:
                attendance.check_out_status = False
                attendance.check_out_difference = 0.0

    @api.depends("employee_id", "working_schedule_id", "check_in", "check_out")
    def _compute_worked_hours(self):
        worked_hours = 0.0
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                worked_hours = (
                    attendance.check_out - attendance.check_in
                ).total_seconds() / 3600.0

            attendance.worked_hours = worked_hours

    @api.depends("employee_id", "working_schedule_id", "start_break", "end_break")
    def _compute_total_break(self):
        total_break = total_over_break = 0.0
        for attendance in self:
            if attendance.start_break and attendance.end_break:
                if attendance.start_break <= attendance.end_break:
                    total_break = (
                        attendance.end_break - attendance.start_break
                    ).total_seconds() / 3600.0

                if total_break > attendance.maximum_break:
                    total_over_break = total_break - attendance.maximum_break

            attendance.total_break = total_break
            attendance.total_over_break = total_over_break

    @api.depends(
        "employee_id",
        "working_schedule_id",
        "worked_hours",
        "check_out",
        "worked_hours",
    )
    def _compute_attendance_status(self):
        for attendance in self:
            if (
                attendance.check_in
                and attendance.check_out
                and attendance.worked_hours > 0.0
            ):
                if attendance.worked_hours >= attendance.minimum_hours:
                    attendance.attendance_status = "present"
                else:
                    attendance.attendance_status = "absent"
            else:
                attendance.attendance_status = False

    @api.depends("employee_id", "start_working_date")
    def _compute_working_schedule(self):
        day_maps = {
            "Monday": "0",
            "Tuesday": "1",
            "Wednesday": "2",
            "Thursday": "3",
            "Friday": "4",
            "Saturday": "5",
            "Sunday": "6",
        }
        for attendance in self:
            if attendance.employee_id or attendance.start_working_date:
                str_day = attendance.start_working_date.strftime("%A")
                day_index = day_maps.get(str_day)
                schedule = self.env["hr.employee.working.calendar"].search(
                    [
                        ("employee_id", "=", attendance.employee_id.id),
                        ("date_start", "=", attendance.start_working_date),
                    ],
                    limit=1,
                )
                if schedule:
                    if schedule.working_hours:
                        working_schedule = schedule.working_hours
                        attendance.working_schedule_id = working_schedule.id
                        attendance.set_working_schedule_values(
                            working_schedule, attendance.start_working_date, day_index
                        )
                    else:
                        contract = self.env["hr.contract"].search(
                            [("employee_id", "=", attendance.employee_id.id)],
                            order="id desc",
                            limit=1,
                        )
                        if contract:
                            working_schedule = contract.resource_calendar_id
                            attendance.working_schedule_id = working_schedule.id
                            attendance.set_working_schedule_values(
                                working_schedule, attendance.start_working_date, day_index
                            )
                        else:
                            attendance.reset_working_schedule_values()
                else:
                    contract = self.env["hr.contract"].search(
                        [("employee_id", "=", attendance.employee_id.id)],
                        order="id desc",
                        limit=1,
                    )
                    if contract:
                        working_schedule = contract.resource_calendar_id
                        attendance.working_schedule_id = working_schedule.id
                        attendance.set_working_schedule_values(
                            working_schedule, attendance.start_working_date, day_index
                        )
                    else:
                        attendance.reset_working_schedule_values()
            else:
                attendance.reset_working_schedule_values()
