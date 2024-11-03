from odoo import models, fields

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    def write(self, vals):
        res = super(HrDepartment, self).write(vals)
        for rec in self:
            employees = self.env['hr.employee'].sudo().search([('department_id','=',rec.id)])
            for emp in employees:
                data_exp_lines = []
                for exp_line in rec.department_expense_line:
                    emp_exp_lines = []
                    for emp_exp_line in emp.employee_expense_line:
                        emp_exp_lines.append(emp_exp_line.product_id.id)
                    if exp_line.product_id.id not in emp_exp_lines:
                        data_exp_lines.append((0, 0, {'product_id': exp_line.product_id.id, 'limit': exp_line.limit}))
                emp.employee_expense_line = data_exp_lines
        return res