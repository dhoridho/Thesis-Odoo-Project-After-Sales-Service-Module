from odoo import _, api, fields, models


class CashAdvanceOverBudgetValidationWizard(models.TransientModel):
    _name = 'cash.advance.over.budget.validation.wizard'
    _description = 'Cash Advance Over Budget Validation Wizard'

    cash_advance_id = fields.Many2one('vendor.deposit', string='Vendor Deposit')
    is_approval_matrix = fields.Boolean(string='Is Approval Matrix', default=False)
    warning_message = fields.Text(string='Warning Message', readonly=True, compute='_compute_warning_message')

    @api.depends('cash_advance_id')
    def _compute_warning_message(self):
        for rec in self:
            rec.warning_message = False
            if rec.cash_advance_id:
                product_name = rec.cash_advance_id.material_overhead_id.product_id.name if rec.cash_advance_id.material_overhead_id else ''
                amt_left = 0
                if rec.cash_advance_id.budgeting_period == 'project':
                    amt_left = rec.cash_advance_id.material_overhead_id.budgeted_amt_left if rec.cash_advance_id.material_overhead_id else 0
                elif rec.cash_advance_id.budgeting_period == 'monthly':
                    amt_left = rec.cash_advance_id.budget_overhead_id.amt_left if rec.cash_advance_id.budget_overhead_id else 0
                    
                rec.warning_message = _("Budget Amount Left for %s is: %d.\nExpense will over the budget plan, are you sure want to continue?" % (product_name, amt_left))

    def action_confirm(self):
        for rec in self:
            rec.cash_advance_id.write({'is_continue_over_budget': True})
            return rec.cash_advance_id.action_pay_cash_advance()