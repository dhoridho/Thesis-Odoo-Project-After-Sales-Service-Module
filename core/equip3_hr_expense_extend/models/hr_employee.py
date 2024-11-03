from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.onchange('department_id')
    def _onchange_department_id(self):
        super(HrEmployee, self)._onchange_department_id()
        for rec in self:
            if rec.department_id:
                rec.employee_expense_line = [(5,0,0)]
                if rec.department_id.department_expense_line:
                    data_exp_lines = []
                    for exp_line in rec.department_id.department_expense_line:
                        data_exp_lines.append((0, 0, {'product_id': exp_line.product_id.id, 'limit': exp_line.limit}))
                    rec.employee_expense_line = data_exp_lines