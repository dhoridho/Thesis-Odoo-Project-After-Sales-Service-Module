# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, exceptions, _, SUPERUSER_ID


class HrEmployeeBaseInherit(models.AbstractModel):
    _inherit = "hr.employee.base"

    last_start_break = fields.Datetime(
        related="last_attendance_id.start_break", store=True
    )
    last_end_break = fields.Datetime(related="last_attendance_id.end_break", store=True)
    break_state = fields.Selection(
        string="Break Status",
        compute="_compute_break_state",
        selection=[("checked_out", "Checked out"), ("checked_in", "Checked in")],
    )
    break_hours_today = fields.Float(compute="_compute_break_hours_today")

    def _compute_break_hours_today(self):
        now = fields.Datetime.now()
        now_utc = pytz.utc.localize(now)
        for employee in self:
            # start of day in the employee's timezone might be the previous day in utc
            tz = pytz.timezone(employee.tz)
            now_tz = now_utc.astimezone(tz)
            start_tz = now_tz + relativedelta(
                hour=0, minute=0
            )  # day start in the employee's timezone
            start_naive = start_tz.astimezone(pytz.utc).replace(tzinfo=None)

            attendances = self.env["hr.attendance"].search(
                [
                    ("employee_id", "=", employee.id),
                    ("start_break", "<=", now),
                    "|",
                    ("end_break", ">=", start_naive),
                    ("end_break", "=", False),
                ]
            )

            worked_hours = 0
            for attendance in attendances:
                delta = (attendance.end_break or now) - max(
                    attendance.start_break, start_naive
                )
                worked_hours += delta.total_seconds() / 3600.0
            employee.break_hours_today = worked_hours

    @api.depends(
        "last_attendance_id.start_break",
        "last_attendance_id.end_break",
        "last_attendance_id",
    )
    def _compute_break_state(self):
        for employee in self:
            att = employee.last_attendance_id.sudo()
            if att.start_break:
                if att.end_break:
                    employee.break_state = "checked_out"
                else:
                    employee.break_state = "checked_in"
            else:
                employee.break_state = "checked_out"
            

    def break_manual(self, next_action, entered_pin=None):
        self.ensure_one()
        can_check_without_pin = not self.env.user.has_group(
            "hr_attendance.group_hr_attendance_use_pin"
        ) or (self.user_id == self.env.user and entered_pin is None)
        if (
            can_check_without_pin
            or entered_pin is not None
            and entered_pin == self.sudo().pin
        ):
            return self._break_action(next_action)
        return {"warning": _("Wrong PIN")}

    def _break_action(self, next_action):
        """Changes the attendance of the employee.
        Returns an action to the start/end break message,
        next_action defines which menu the start/end message should return to. ("My Attendances" or "Kiosk Mode")
        """
        self.ensure_one()
        employee = self.sudo()
        action_message = self.env["ir.actions.actions"]._for_xml_id(
            "hr_attendance.hr_attendance_action_greeting_message"
        )
        action_message["previous_attendance_change_date"] = (
            employee.last_attendance_id
            and (
                employee.last_attendance_id.check_out
                or employee.last_attendance_id.check_in
            )
            or False
        )
        action_message["employee_name"] = employee.name
        action_message["barcode"] = employee.barcode
        action_message["next_action"] = next_action
        action_message["hours_today"] = employee.hours_today
        action_message["break_hours_today"] = employee.break_hours_today

        if employee.user_id:
            modified_attendance = employee.with_user(
                employee.user_id
            )._break_action_change()
        else:
            modified_attendance = employee._break_action_change()
        action_message["attendance"] = modified_attendance.read()[0]
        return {"action": action_message}

    def _break_action_change(self):
        self.ensure_one()
        action_date = fields.Datetime.now()

        start_break_attendance = self.env["hr.attendance"].search(
            [("employee_id", "=", self.id), ("start_break", "=", False)], limit=1
        )
        if start_break_attendance:
            start_break_attendance = self.env["hr.attendance"].search(
                [("employee_id", "=", self.id), ('start_break', '=', False)], limit=1
            )
            start_break_attendance.start_break = action_date
            return start_break_attendance

        end_break_attendance = self.env["hr.attendance"].search(
            [("employee_id", "=", self.id), ("end_break", "=", False)], limit=1
        )
        if end_break_attendance:
            end_break_attendance.end_break = action_date
        else:
            raise exceptions.UserError(
                _(
                    "Cannot perform check out on %(empl_name)s, could not find corresponding check in. "
                    "Your attendances have probably been modified manually by human resources."
                )
                % {
                    "empl_name": self.sudo().name,
                }
            )
        return end_break_attendance
