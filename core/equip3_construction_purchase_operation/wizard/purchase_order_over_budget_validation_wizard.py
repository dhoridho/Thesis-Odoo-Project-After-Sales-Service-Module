from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class PurchaseOrderOverBudgetValidationWizard(models.TransientModel):
    _name = 'purchase.order.over.budget.validation.wizard'
    _description = 'Purchase Order Over Budget Validation Wizard'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    budgeting_method = fields.Selection(related='purchase_order_id.budgeting_method', string='Budgeting Method')
    is_approval_matrix = fields.Boolean(string='Is Approval Matrix', default=False)
    warning_message = fields.Text(string='Warning Message', readonly=True, compute='_compute_warning_message')

    @api.depends('purchase_order_id')
    def _compute_warning_message(self):
        for rec in self:
            rec.warning_message = False
            if rec.purchase_order_id:
                rec.warning_message = _("Expense will over the budget plan, are you sure want to continue?")

    def action_confirm(self):
        for rec in self:
            rec.purchase_order_id.write({'is_continue_over_budget': True})
            return rec.purchase_order_id.button_confirm()