from odoo import api, fields, models
from datetime import datetime

class ApprovalMatrixExpensePlan(models.Model):
    _name = 'approval.matrix.expense.plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Expense Plan Approval Matrix'
    

    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.user.company_id, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True)
    created_date = fields.Date(string='Create On', default=datetime.today().date(), readonly=True)
    user_id = fields.Many2one('res.users', 'Created By', required=True, readonly=True, default=lambda self: self.env.user)
    min_amount = fields.Float(string='Minimum Amount', required=True)
    max_amount = fields.Float(string='Maximum Amount', required=True)
    approval_matrix_expense_plan_line_ids = fields.One2many('approval.matrix.expense.plan.line', 'approval_matrix_expense_plan_id', string='Approval')



class ApprovalMatrixExpensePlanLines(models.Model):
    _name = 'approval.matrix.expense.plan.line'
    _description = "Approval Matrix Expense Plan"

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixExpensePlanLines, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_expense_plan_line_ids' in context_keys:
                if len(self._context.get('approval_matrix_expense_plan_line_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_expense_plan_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    approval_matrix_expense_plan_id = fields.Many2one('approval.matrix.expense.plan')
    user_name_ids = fields.Many2many('res.users', string="Users", required=True)
    min_approvers = fields.Integer(string='Minimum Approvers', required=True, default=1)
    sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence', tracking=True)
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True,
        tracking=True
    )
