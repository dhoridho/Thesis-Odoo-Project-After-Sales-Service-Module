
from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class ApprovalMatrixCostSheetReject(models.TransientModel):
    _name = 'approval.matrix.cost.sheet.reject'
    _description = "Approval Matrix Cost Sheet Reject"

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        cost_id = self.env['job.cost.sheet'].browse([self._context.get('active_id')])
        approving_matrix_line = sorted(cost_id.cost_sheet_user_ids.filtered(lambda r: r.is_approve == False))
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            matrix_line.write({'feedback': self.reason})
            cost_id.action_reject_approval() 


class ApprovalMatrixProjectBudgetReject(models.TransientModel):
    _name = 'approval.matrix.project.budget.reject'
    _description = "Approval Matrix Project Budget Reject"

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        budget_id = self.env['project.budget'].browse([self._context.get('active_id')])
        approving_matrix_line = sorted(budget_id.project_budget_user_ids.filtered(lambda r: r.is_approve == False))
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            matrix_line.write({'feedback': self.reason})
            budget_id.action_reject_approval() 


class ApprovalMatrixInternalBudgetReject(models.TransientModel):
    _name = 'approval.matrix.internal.budget.reject'
    _description = "Approval Matrix Internal Budget Reject"

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        internal_id = self.env['internal.transfer.budget'].browse([self._context.get('active_id')])
        approving_matrix_line = sorted(internal_id.budget_change_user_ids.filtered(lambda r: r.is_approve == False))
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            matrix_line.write({'feedback': self.reason})
            internal_id.action_reject_approval()


class ApprovalMatrixBudgetCarryReject(models.TransientModel):
    _name = 'approval.matrix.budget.carry.reject'
    _description = "Approval Matrix Budget Carry Reject"

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        internal_id = self.env['project.budget.carry'].browse([self._context.get('active_id')])
        approving_matrix_line = sorted(internal_id.budget_carry_user_ids.filtered(lambda r: r.is_approve == False))
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            matrix_line.write({'feedback': self.reason})
            internal_id.action_reject_approval()


class ApprovalMatrixAssetallocationReject(models.TransientModel):
    _name = 'approval.matrix.asset.allocation.reject'
    _description = "Approval Matrix Asset Allocation Reject"

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        internal_id = self.env['allocation.asset.line'].browse([self._context.get('active_id')])
        approving_matrix_line = sorted(internal_id.asset_allocation_user_ids.filtered(lambda r: r.is_approve == False))
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            matrix_line.write({'feedback': self.reason})
            internal_id.action_reject_approval()