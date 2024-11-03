import calendar
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
import time
from odoo.exceptions import ValidationError
import xlwt
import base64
from io import BytesIO


class HrSgAttendanceReport(models.TransientModel):
    _name = 'hr.attendance.report.wizard'
    _description = 'HR SG Attendance Report'

    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    specify_by = fields.Selection(
        selection=[
            ('department', 'Department'),
            ('employee', 'Employee')
        ],
        string='Specify By',
        default='employee'
    )
    all_departments = fields.Boolean('All Departments', default=False)
    department_ids = fields.Many2many('hr.department', string='Department')
    all_employees = fields.Boolean('All Employees', default=False)
    employee_ids = fields.Many2many('hr.employee', string='Employee')
    print_as = fields.Selection(
        selection=[
            ('xls', 'XLS'),
            ('pdf', 'PDF')
        ],
        string='Print As',
        default='xls'
    )

    @api.onchange('all_departments')
    def onchange_all_department(self):
        for rec in self:
            if rec.all_departments:
                dept_obj = self.env[('hr.department')].search(
                    [('active', '=', True)])
                dept_ids = []
                for dept in dept_obj:
                    dept_ids.append(dept.id)
                rec.department_ids = dept_ids
            else:
                rec.department_ids = [(5, 0, 0)]

    @api.onchange('all_employees')
    def onchange_all_employee(self):
        for rec in self:
            if rec.all_employees:
                emp_obj = self.env[('hr.employee')].search(
                    [('active', '=', True)])
                emp_ids = []
                for emp in emp_obj:
                    emp_ids.append(emp.id)
                rec.employee_ids = emp_ids
            else:
                rec.employee_ids = [(5, 0, 0)]

    @api.constrains('date_from', 'date_from')
    def _check_date_ranges(self):
        if self.date_from > self.date_to:
            raise ValidationError("Date To must be greater than Date From")

    @api.constrains('date_from', 'date_to', 'specify_by', 'employee_ids')
    def _check_attendance_report(self):
        result = self._sql_query()
        if not result:
            raise ValidationError(_("There is no data in selected date."))

    def _sql_query(self):
        query = """
            SELECT
                e.id AS employee_id, e.identification_id, e.name AS employee_name,
                d.name AS department,
                j.name AS job_position,
                a.check_in, a.check_out,
                a.worked_hours,
                a.check_in::date AS checkin_date,
                a.check_in::text AS checkin_date_str
            FROM hr_employee e
            LEFT JOIN hr_attendance a ON e.id = a.employee_id
            LEFT JOIN hr_department d ON e.department_id = d.id
            LEFT JOIN hr_job j ON e.job_id = j.id
            WHERE e.active = TRUE
                AND a.check_in >= %s
                AND a.check_in <= %s
                AND e.id IN %s
            ORDER BY e.id, a.check_in
        """

        self.env.cr.execute(
            query, (self.date_from, self.date_to, tuple(self.employee_ids.ids)))
        result = self.env.cr.dictfetchall()

        return result

    def get_report_data(self):
        attendance_data = []

        # Constructing the period string
        period = (
            str(self.date_from.strftime("%d"))
            + "/"
            + str(self.date_from.strftime("%m"))
            + "/"
            + str(self.date_from.strftime("%Y"))
            + " to "
            + str(self.date_to.strftime("%d"))
            + "/"
            + str(self.date_to.strftime("%m"))
            + "/"
            + str(self.date_to.strftime("%Y"))
        )
        result = self._sql_query()
        attendances_dict = {}

        for row in result:
            emp_id = row["employee_id"]
            attendances_dict['period'] = period

            if emp_id not in attendances_dict:
                attendances_dict[emp_id] = {
                    'identification_id': row["identification_id"],
                    'employee_id': emp_id,
                    'employee_name': row["employee_name"],
                    'department': row["department"] if row["department"] else "-",
                    'job_position': row["job_position"] if row["job_position"] else "-",
                    'attendances': {},
                    'period': period,
                }

            checkin_date_str = row["checkin_date_str"]
            if checkin_date_str not in attendances_dict[emp_id]['attendances']:
                attendances_dict[emp_id]['attendances'][checkin_date_str] = {
                    'dates': row["checkin_date"],
                    'day': row["check_in"].strftime('%A'),
                    'check_in': row["check_in"],
                    'check_out': row["check_out"] if row["check_out"] else '-',
                    'worked_hours': round(row["worked_hours"], 2),
                }

        attendance_data.append(attendances_dict)

        return attendance_data

    def action_print(self):
        report_id = self.env.ref(
            'equip3_hr_sg_reports.hr_attendance_action_report'
        )
        return report_id.report_action(self)
