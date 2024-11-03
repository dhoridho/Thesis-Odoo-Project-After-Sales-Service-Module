from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class PurchaseOrderOverBudgetValidation(models.TransientModel):
    _name = 'internal.transfer.budget.over.budget.validation'
    _description = 'Internal Transfer Over Budget Validation Wizard'

    itb_id = fields.Many2one('internal.transfer.budget', string='Internal Transfer Budget')
    budgeting_method = fields.Selection(related='itb_id.budgeting_method', string='Budgeting Method')
    is_approval_matrix = fields.Boolean(string='Is Approval Matrix', default=False)
    warning_message = fields.Text(string='Warning Message', readonly=True)

    def action_confirm(self):
        for rec in self:
            rec.itb_id.write({'is_continue_over_budget': True})
            if rec.is_approval_matrix:
                return rec.itb_id.request_approval()
            else:
                return rec.itb_id.confirm()