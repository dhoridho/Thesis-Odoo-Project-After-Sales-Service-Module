from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, datetime, time, timedelta
from pytz import timezone
from dateutil.rrule import rrule, DAILY
import pytz


class HrPayslipInherit(models.Model):
    _inherit = "hr.payslip"

    late_deduction_ids = fields.One2many(
        comodel_name="hr.payslip.late.deduction",
        inverse_name="payslip_id",
        string="Late Deduction",
    )
    under_time_deduction_ids = fields.One2many(
        comodel_name="hr.payslip.under.time.deduction",
        inverse_name="payslip_id",
        string="Under Time Deduction",
    )
    over_break_deduction_ids = fields.One2many(
        comodel_name="hr.payslip.over.break.deduction",
        inverse_name="payslip_id",
        string="Over Break Deduction",
    )
    total_deduction = fields.Float("Total Deduction")
    total_under_time_deduction = fields.Float("Total Deduction")
    total_over_break_deduction = fields.Float("Total Deduction")

    @api.model
    def default_get(self, fields):
        res = super(HrPayslipInherit, self).default_get(fields)
        res.update(
            {
                "worked_days_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": _("Normal Working Days paid at 100%"),
                            "sequence": 1,
                            "code": "WORK100",
                            "number_of_days": 0,
                            "number_of_hours": 0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": _("Total Absences Per Period"),
                            "sequence": 2,
                            "code": "COUNT_ABSENT",
                            "number_of_days": 0,
                            "number_of_hours": 0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": _("Total Presents Per Period"),
                            "sequence": 3,
                            "code": "COUNT_PRESENT",
                            "number_of_days": 0,
                            "number_of_hours": 0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": _("Total Late Deduction"),
                            "sequence": 4,
                            "code": "COUNT_LATE",
                            "number_of_days": 0,
                            "number_of_hours": 0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": _("Total Under Time"),
                            "sequence": 5,
                            "code": "COUNT_UNDER_TIME",
                            "number_of_days": 0,
                            "number_of_hours": 0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": _("Total Over Break"),
                            "sequence": 6,
                            "code": "COUNT_OVER_BREAK",
                            "number_of_days": 0,
                            "number_of_hours": 0,
                        },
                    ),
                ],
            }
        )

        return res

    @api.model
    def create(self, vals):
        if "worked_days_line_ids" in vals and "employee_id" in vals:
            contract = self.env["hr.contract"].search(
                [("employee_id", "=", vals.get("employee_id"))],
                order="create_date DESC",
                limit=1,
            )
            employee = self.env["hr.employee"].browse(vals.get("employee_id"))
            if not contract:
                raise UserError(
                    _("Employee %s does not have contract" % (employee.name))
                )
        res = super(HrPayslipInherit, self).create(vals)
        return res

    def get_worked_day_records(self, contract, calendar):
        count_absent = 0
        total_selected_calendar = 0
        count_total_late_deduction = 0
        count_total_under_time = 0
        count_total_over_break = 0

        for payslip in self:
            start_date = fields.Date.from_string(payslip.date_from)
            end_date = fields.Date.from_string(payslip.date_to)
            dates = list(rrule(DAILY, dtstart=start_date, until=end_date))

            employee_working_calendars = self.env[
                "hr.employee.working.calendar"
            ].search(
                [
                    ("working_hours", "=", calendar.id),
                    ("employee_id", "=", contract.employee_id.id),
                ]
            )

            attendances = self.env["hr.attendance"].search(
                [
                    ("working_schedule_id", "=", calendar.id),
                    ("employee_id", "=", contract.employee_id.id),
                ]
            )

            attendance_dates = {attendance.start_working_date for attendance in attendances}
            seen_dates = set()

            for employee_calendar in employee_working_calendars.filtered(
                lambda calendar: calendar.date_start not in seen_dates and not seen_dates.add(calendar.date_start) and calendar.day_type == "work_day"
            ):
                calendar_dates = [
                    date for date in dates
                    if employee_calendar.date_start <= date.date() <= employee_calendar.date_end
                ]

                for date in calendar_dates:
                    # Calculate total absent
                    if date.date() not in attendance_dates:
                        count_absent += 1
                    
                    # Calculate total working calendar
                    total_selected_calendar += 1

                    for attendance in attendances:
                        if employee_calendar.date_start == attendance.start_working_date:
                            user_tz = self.env.user.tz or "UTC"
                            local_tz = pytz.timezone(user_tz)
                            check_in_local = pytz.utc.localize(
                                fields.Datetime.from_string(attendance.check_in)
                            ).astimezone(local_tz)

                            total_allowed_time = attendance.hour_from + attendance.tolerance_late
                            allowed_time_delta = timedelta(
                                hours=int(total_allowed_time), 
                                minutes=int((total_allowed_time % 1) * 60)
                            )
                            expected_check_in_time = local_tz.localize(
                                datetime.combine(check_in_local.date(), datetime.min.time())
                            ) + allowed_time_delta

                            # Calculate total late deduction
                            if attendance.check_in_status == "late":
                                count_total_late_deduction += (
                                    (check_in_local - expected_check_in_time).total_seconds() / 3600
                                )

                            # Calculate total under time
                            if attendance.check_out_status == "not_fulfill":
                                count_total_under_time += attendance.check_out_difference

                            # Calculate total over break
                            if attendance.start_break and attendance.end_break:
                                check_out_break_local = pytz.utc.localize(
                                    fields.Datetime.from_string(attendance.start_break)
                                ).astimezone(local_tz)
                                check_in_break_local = pytz.utc.localize(
                                    fields.Datetime.from_string(attendance.end_break)
                                ).astimezone(local_tz)
                                check_in_out_break_difference = (
                                    (check_in_break_local - check_out_break_local).total_seconds() / 3600
                                )
                                if check_in_out_break_difference > attendance.maximum_break:
                                    count_total_over_break += check_in_out_break_difference - attendance.maximum_break

        return {
            "absent_days": count_absent,
            "present_days": total_selected_calendar - count_absent,
            "total_late_deduction": count_total_late_deduction,
            "total_under_time": count_total_under_time,
            "total_over_break": count_total_over_break,
        }

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(
            lambda contract: contract.resource_calendar_id
        ):
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)

            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(
                day_from, day_to, calendar=contract.resource_calendar_id
            )
            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                current_leave_struct = leaves.setdefault(
                    holiday.holiday_status_id,
                    {
                        "name": holiday.holiday_status_id.name or _("Global Leaves"),
                        "sequence": 5,
                        "code": holiday.holiday_status_id.code or "GLOBAL",
                        "number_of_days": 0.0,
                        "number_of_hours": 0.0,
                        "contract_id": contract.id,
                    },
                )
                current_leave_struct["number_of_hours"] += hours
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if work_hours:
                    current_leave_struct["number_of_days"] += hours / work_hours

            # compute worked days
            
            work_data = contract.employee_id.get_work_days_data(
                day_from, day_to, calendar=contract.resource_calendar_id
            )

            if contract.resource_calendar_id.schedule == "shift_pattern":
                work_data = contract.resource_calendar_id.get_shift_work_days_data(
                    day_from, day_to
                )

            attendances = {
                "name": _("Normal Working Days paid at 100%"),
                "sequence": 1,
                "code": "WORK100",
                "number_of_days": work_data["days"],
                "number_of_hours": work_data["hours"],
                "contract_id": contract.id,
            }
            res.append(attendances)
            res.extend(leaves.values())

            working_calendar = self.get_worked_day_records(contract, calendar)
            res.append(
                {
                    "name": _("Total Absent Per Period"),
                    "sequence": 2,
                    "code": "COUNT_ABSENT",
                    "number_of_days": working_calendar["absent_days"],
                    "number_of_hours": 0.0,
                    "contract_id": contract.id,
                }
            )

            res.append(
                {
                    "name": _("Total Present Per Period"),
                    "sequence": 3,
                    "code": "COUNT_PRESENT",
                    "number_of_days": working_calendar["present_days"],
                    "number_of_hours": 0.0,
                    "contract_id": contract.id,
                }
            )

            res.append(
                {
                    "name": _("Total Late Deduction"),
                    "sequence": 4,
                    "code": "COUNT_LATE",
                    "number_of_days": 0.0,
                    "number_of_hours": working_calendar["total_late_deduction"],
                    "contract_id": contract.id,
                }
            )

            res.append(
                {
                    "name": _("Total Under Time"),
                    "sequence": 5,
                    "code": "COUNT_UNDER_TIME",
                    "number_of_days": 0.0,
                    "number_of_hours": working_calendar["total_under_time"],
                    "contract_id": contract.id,
                }
            )

            res.append(
                {
                    "name": _("Total Over Break"),
                    "sequence": 6,
                    "code": "COUNT_OVER_BREAK",
                    "number_of_days": 0.0,
                    "number_of_hours": working_calendar["total_over_break"],
                    "contract_id": contract.id,
                }
            )
        return res
