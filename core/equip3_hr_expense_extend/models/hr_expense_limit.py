from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrExpenseCycleExtend(models.Model):
    _inherit = "hr.expense.cycle"

    apply_to = fields.Selection(
        string="Apply To",
        selection=[
            ("by_employee", "By Employee"),
            ("by_job_position", "By Job Position"),
            ("by_department", "By Department"),
            ("by_company", "By Company"),
        ],
        default="by_employee",
    )
    employee_id = fields.Many2many(
        string="Employee",
        comodel_name="hr.employee",
    )
    job_id = fields.Many2many(
        string="Job Position",
        comodel_name="hr.job",
    )
    department_id = fields.Many2many(
        string="Department",
        comodel_name="hr.department",
    )
    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
    )
    expense_limit_line_ids = fields.One2many(
        comodel_name="hr.expense.limit.line",
        inverse_name="expense_cycle_id",
        string="Expense Limit Line",
    )


class HrExpenseLimitLine(models.Model):
    _name = "hr.expense.limit.line"
    _description = "HR Expense Limit Line"

    product_id = fields.Many2one(
        string="Product",
        comodel_name="product.product",
        domain=[("can_be_expensed", "=", True)],
        ondelete="cascade",
    )
    limit = fields.Float(string="Limit", default=0)
    limit_type = fields.Selection(
        [
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
        ],
        string="Limit Type",
        copy=False,
        index=True,
        default="monthly",
    )
    expense_cycle_id = fields.Many2one(
        string="Expense Limit",
        comodel_name="hr.expense.cycle",
        ondelete="cascade",
    )


# class HrExpenseExtend(models.Model):
#     _inherit = "hr.expense"

#     @api.model
#     def create(self, vals):
#         res = super(HrExpenseExtend, self).create(vals)
#         expense_date = res.date
#         expense_year = expense_date.strftime("%Y")
#         expense_cycles = self.env["hr.expense.cycle"].search([
#             ("hr_year_id.name", "=", expense_year)
#         ])
#         if expense_cycles:
#             for expense in expense_cycles:
#                 employees_ids = False
#                 if expense.apply_to == "by_employee":
#                     employees_ids = expense.employee_id.ids
#                 elif expense.apply_to == "by_job_position":
#                     employees = self.env["hr.employee"].search(
#                         [("job_id", "in", expense.job_id.ids)]
#                     )
#                     employees_ids = employees.ids
#                 elif expense.apply_to == "by_department":
#                     employees = self.env["hr.employee"].search(
#                         [("department_id", "in", expense.department_id.ids)]
#                     )
#                     employees_ids = employees.ids
#                 elif expense.apply_to == "by_company":
#                     employees = self.env["hr.employee"].search(
#                         [("company_id", "=", expense.company_id.id)]
#                     )
#                     employees_ids = employees.ids

#                 for limit_line in expense.expense_limit_line_ids:
#                     if res.employee_id.id in employees_ids and res.product_id.id == limit_line.product_id.id:
#                         if res.total_amount > limit_line.limit:
#                             raise ValidationError(
#                                 f"Unbalance limit please ask your responsible user for increase the limit"
#                             )

#         else:
#             raise ValidationError(
#                 "There is no available period for this expense"
#             )
#         return res

#     def write(self, vals):
#         res = super(HrExpenseExtend, self).write(vals)
#         for expense in self:
#             expense_date = expense.date
#             expense_year = expense_date.strftime("%Y")
#             expense_cycles = self.env["hr.expense.cycle"].search([
#                 ("hr_year_id.name", "=", expense_year)
#             ])
#             if expense_cycles:
#                 employees_ids = False
#                 if expense_cycles.apply_to == "by_employee":
#                     employees_ids = expense_cycles.employee_id.ids
#                 elif expense_cycles.apply_to == "by_job_position":
#                     employees = self.env["hr.employee"].search(
#                         [("job_id", "in", expense_cycles.job_id.ids)]
#                     )
#                     employees_ids = employees.ids
#                 elif expense_cycles.apply_to == "by_department":
#                     employees = self.env["hr.employee"].search(
#                         [("department_id", "in", expense_cycles.department_id.ids)]
#                     )
#                     employees_ids = employees.ids
#                 elif expense_cycles.apply_to == "by_company":
#                     employees = self.env["hr.employee"].search(
#                         [("company_id", "=", expense_cycles.company_id.id)]
#                     )
#                     employees_ids = employees.ids

#                 if expense.employee_id.id in employees_ids:
#                     for limit_line in expense_cycles.expense_limit_line_ids:
#                         if expense.product_id.id == limit_line.product_id.id:
#                             if expense.total_amount > limit_line.limit:
#                                 raise ValidationError(
#                                     f"Unbalance limit please ask your responsible user for increase the limit"
#                                 )
#             else:
#                 raise ValidationError(
#                     "There is no available period for this expense"
#                 )

#             return res
