from odoo import api, fields, models, _
from datetime import timedelta


class HrEmployeeWorkingCalendar(models.Model):
    _name = "hr.employee.working.calendar"
    _description = "Employee Working Calendar"
    _order = "employee_id"

    WEEKDAYS = [
        ("0", "Monday"),
        ("1", "Tuesday"),
        ("2", "Wednesday"),
        ("3", "Thursday"),
        ("4", "Friday"),
        ("5", "Saturday"),
        ("6", "Sunday"),
    ]

    name = fields.Char(
        string="Name", size=256, required=0, compute="get_break_from_and_to"
    )
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee")
    contract_id = fields.Many2one(comodel_name="hr.contract", string="Contract")
    department_id = fields.Many2one(comodel_name="hr.department", string="Department")
    working_hours = fields.Many2one(
        comodel_name="resource.calendar", string="Working Schedule"
    )
    day_of_week = fields.Selection(WEEKDAYS, string="Name of Day")
    date_start = fields.Date(string="Start Date", required=True)
    date_end = fields.Date(string="End Date", required=True)
    hour_from = fields.Float(string="Work From")
    hour_to = fields.Float(string="Work To")
    tolerance_late = fields.Float("Tolerance for Late")
    break_from = fields.Float("Break From")
    break_to = fields.Float("Break To")
    minimum_hours = fields.Float("Minimum Hours")
    checkin = fields.Datetime("Start Working Times")
    checkout = fields.Datetime("End Working Times")
    is_generated = fields.Boolean('Is Generated')
    maximum_break = fields.Float(string="Maximum Break")
    day_type = fields.Selection(
        selection=[
            ("work_day", "Work Day"),
            ("day_off", "Day Off"),
            ("public_holiday", "Public Holiday")
        ],
        string="Day Type",
        default="work_day",
    )

    @api.onchange("employee_id")
    def onchange_department(self):
        for record in self:
            if record.employee_id:
                record.contract_id = record.employee_id.contract_id.id
                record.department_id = record.employee_id.department_id.id
                record.working_hours = record.employee_id.resource_calendar_id.id
            else:
                record.contract_id = False
                record.department_id = False
                record.working_hours = False

    def get_break_from_and_to(self):
        for record in self:
            if record.date_start and record.date_end:
                start_time = timedelta(hours=record.hour_from)
                end_time = timedelta(hours=record.hour_to)

                record.name = (
                    record.employee_id.name
                    + " "
                    + str(start_time)[:-3]
                    + " - "
                    + str(end_time)[:-3]
                )
            else:
                record.name = False
