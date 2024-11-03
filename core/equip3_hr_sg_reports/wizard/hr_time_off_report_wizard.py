from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrSgTimeOffReport(models.TransientModel):
    _name = 'hr.timeoff.report.wizard'
    _description = 'HR SG Time Off Report'

    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    all_employees = fields.Boolean('All Employees', default=False)
    employee_ids = fields.Many2many('hr.employee', string='Employee')

    @api.onchange('all_employees')
    def onchange_all_employee(self):
        for rec in self:
            if rec.all_employees:
                emp_obj = self.env[('hr.employee')].search(
                    [('active', '=', True)]
                )
                emp_ids = []
                for emp in emp_obj:
                    emp_ids.append(emp.id)
                rec.employee_ids = emp_ids
            else:
                rec.employee_ids = [(5, 0, 0)]

    def _get_selection_display_name(self, field, val):
        leaves = self.env['hr.leave'].search([])
        for option_val, name in leaves._fields[field].selection:
            if option_val == val:
                return name
        return val

    @api.constrains('date_from', 'date_to', 'employee_ids')
    def _check_leave_report(self):
        num_of_report = 0
        result = self._sql_query()
        if not result:
            raise ValidationError(_("There is no Employee Data on specific selection."))

        for leave in result:
            start_date = leave["date_from"]
            if start_date and start_date.date() >= self.date_from and start_date.date() <= self.date_to:
                num_of_report += 1
        
        if num_of_report < 1:
            raise ValidationError("There is no data in selected date.")

    def _sql_query(self):
        query = """
            SELECT e.id AS employee_id, e.identification_id, e.name AS employee_name,
                d.name AS department_name,
                j.name AS job_name,
                l.id AS leave_id, l.holiday_status_id, lt.code AS leave_type_code,
                l.private_name AS description, l.date_from, l.date_to, l.number_of_days, l.state
            FROM hr_employee e
            LEFT JOIN hr_leave l ON e.id = l.employee_id
            LEFT JOIN hr_department d ON e.department_id = d.id
            LEFT JOIN hr_job j ON e.job_id = j.id
            LEFT JOIN hr_leave_type lt ON l.holiday_status_id = lt.id
            WHERE e.active = TRUE AND e.id IN %s
            ORDER BY e.id, l.date_from
        """
        self.env.cr.execute(query, (tuple(self.employee_ids.ids),))
        result = self.env.cr.dictfetchall()

        return result

    def get_report_data(self):
        time_off_data = []

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
        time_off_dict = {}

        for leave in result:
            start_date = leave["date_from"]
            date_from_str = str(start_date) if start_date else ""
            if start_date and start_date.date() >= self.date_from and start_date.date() <= self.date_to:
                emp_id = leave["employee_id"]
                time_off_dict['period'] = period
                if leave['employee_id'] == emp_id:

                    if emp_id not in time_off_dict:
                        time_off_dict[emp_id] = {
                            "identification_id": leave["identification_id"],
                            "employee_id": emp_id,
                            "employee_name": leave["employee_name"],
                            "department": leave["department_name"] if leave["department_name"] else "-",
                            "job_position": leave["job_name"] if leave["job_name"] else "-",
                            "leaves": {},
                        }
                    if date_from_str not in time_off_dict[emp_id]['leaves']:
                        time_off_dict[emp_id]["leaves"][date_from_str] = {
                            "leave_code": leave["leave_type_code"] if leave["leave_type_code"] else "-",
                            "description": leave["description"] if leave["description"] else "-",
                            "start_date": str(leave["date_from"].date()) if leave["date_from"] else "-",
                            "end_date": str(leave["date_to"].date()) if leave["date_to"] else "-",
                            "days": leave["number_of_days"],
                            "status": self._get_selection_display_name("state", leave["state"]),
                        }

        time_off_data.append(time_off_dict)

        return time_off_data

    def action_print(self):
        report_id = self.env.ref(
            'equip3_hr_sg_reports.hr_timeoff_action_report'
        )
        return report_id.report_action(self)
