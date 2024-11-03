from odoo import models, fields, _
from odoo.exceptions import ValidationError


class WizEmployeeLetterUndertaking(models.TransientModel):
    _name = 'wiz.employee.letter.undertaking'
    _description = "Letter Undertaking Wizard"

    employee_ids = fields.Many2many('hr.employee', 'letter_taking_employee',
                                    'lt_employee', 'employee_id', 'Employee')

    def print_report(self):
        data = self.read([])[0]
        employee_ids = data.get('employee_ids', False)
        if len(employee_ids) == 0:
            raise ValidationError(_("Please select employee"))
        report_id = self.env.ref(
            'sg_report_letter_undertaking.sg_report_letter')
        return report_id.report_action(self, data=data, config=False)
