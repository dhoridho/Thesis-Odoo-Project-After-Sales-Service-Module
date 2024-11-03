from odoo import _, api, fields, models


class PettyCashOverBudgetValidationWizard(models.TransientModel):
    _name = 'petty.cash.over.budget.validation.wizard'
    _description = 'Petty Cash Over Budget Validation Wizard'

    petty_cash_id = fields.Many2one('account.pettycash', string='Vendor Deposit')
    is_approval_matrix = fields.Boolean(string='Is Approval Matrix', default=False)
    warning_message = fields.Text(string='Warning Message', readonly=True, compute='_compute_warning_message')

    @api.depends('petty_cash_id')
    def _compute_warning_message(self):
        for rec in self:
            rec.warning_message = False
            if rec.petty_cash_id:
                product_name = rec.petty_cash_id.referred_budget_material.product_id.name if rec.petty_cash_id.referred_budget_material else ''
                amt_left = 0
                if rec.petty_cash_id.budgeting_period == 'project':
                    amt_left = rec.petty_cash_id.referred_budget_material.budgeted_amt_left if rec.petty_cash_id.referred_budget_material else 0
                elif rec.petty_cash_id.budgeting_period == 'monthly':
                    amt_left = rec.petty_cash_id.referred_budget_budget.amt_left if rec.petty_cash_id.referred_budget_budget else 0
                    
                rec.warning_message = _("Budget Amount Left for %s is: %d.\nExpense will over the budget plan, are you sure want to continue?" % (product_name, amt_left))

    def action_confirm(self):
        for rec in self:
            rec.petty_cash_id.write({'is_continue_over_budget': True})
            return rec.petty_cash_id.validate()