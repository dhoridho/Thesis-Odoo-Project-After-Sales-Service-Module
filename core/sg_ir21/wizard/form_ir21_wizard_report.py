import time
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class WizHrEmployeeReport(models.TransientModel):
    _name = 'wiz.hr.employee.report'
    _description = "Hr Employee Report"

    employee_ids = fields.Many2many('hr.employee', 'rel_employee',
                                    'an_employee', 'employee_id', 'Employee')
    start_date = fields.Date("Start Date", default=time.strftime('%Y-01-01'))
    end_date = fields.Date("End Date", default=time.strftime('%Y-12-31'))

    def print_report(self):
        if self.start_date.year != self.end_date.year:
            raise ValidationError(_(
                "Start date and End date must be from same year"))
        if self.start_date > self.end_date:
            raise ValidationError(_(
                "Start Date should be Greater than End Date"))

        data = self.read([])[0]
        employee_ids = data.get('employee_ids')
        if len(employee_ids) == 0:
            raise ValidationError(_("Please select employee"))
        report_id = self.env.ref('sg_ir21.angcrane_employee_report')
        return report_id.report_action(self, data=data, config=False)
