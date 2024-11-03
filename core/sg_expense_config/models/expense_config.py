from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_sg_expense_maxcap = fields.Boolean(
        "Manage Expense Reimbursement Maximum limit per Employee",
        help="This help to add expense product and maximum amount limits \
            configurations in employee's contract, which use in expense \
            claim by user"
    )
    module_sg_expense_payroll = fields.Boolean(
        "Include Expense reimbursement amount in payslips",
        help="This help you to to calculate expenses auto calculation"
    )
