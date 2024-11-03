from odoo import api, fields, models, _


class VendorDeposit(models.Model):
    _inherit = "vendor.deposit"

    crossovered_budget_line_id = fields.Many2one('crossovered.budget.lines', string='Budget Line', compute='_get_crossovered_budget_line', store=True)
    crossovered_budget_id = fields.Many2one('crossovered.budget', related='crossovered_budget_line_id.crossovered_budget_id')
    general_budget_id = fields.Many2one('account.budget.post', string='Budgetary Position')
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")


    @api.depends('analytic_group_ids','payment_date','deposit_account_id')
    def _get_crossovered_budget_line(self):
        for record in self:
            record.crossovered_budget_line_id = False
            budget_lines = self.env['crossovered.budget.lines'].search([
                ('crossovered_budget_id.state', '=', 'validate'),
                ('date_from', '<=', record.payment_date), 
                ('date_to', '>=', record.payment_date),
            ])
            for budget in budget_lines:
                acc_ids = budget.general_budget_id.account_ids.ids
                if record.deposit_account_id.id in acc_ids and any(item in record.analytic_group_ids.ids for item in budget.analytic_group_ids.ids):
                    record.crossovered_budget_line_id = budget.id
                    record.general_budget_id = budget.general_budget_id.id

    def check_overbudget(self):
        exceeding_lines = []
        for record in self:
            if record.crossovered_budget_line_id and record.amount > record.crossovered_budget_line_id.remaining_amount:
                exceeding_lines.append(record)

        return exceeding_lines

    def action_confirm(self):
        exceeding_lines = self.check_overbudget()
        if exceeding_lines:
            wizard = self.env['expense.request.warning'].create({
                'warning_line_ids': [
                    (0, 0, {
                        'budgetary_position_id': line.crossovered_budget_line_id.general_budget_id.id,
                        'account_id': line.deposit_account_id.id,
                        'planned_budget': line.crossovered_budget_line_id.budget_amount,
                        'expense_budget': line.crossovered_budget_line_id.remaining_amount,
                        'realized_amount': line.amount,
                    }) for line in exceeding_lines
                ]
            })
            return {
                'name': 'Warning',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'expense.request.warning',
                'res_id': wizard.id,
                'target': 'new',
            }
        else:
            res = super(VendorDeposit, self).action_confirm()
            return res

    def action_request_approval_cash_advance(self):
        exceeding_lines = self.check_overbudget()
        if exceeding_lines:
            wizard = self.env['expense.request.warning'].create({
                'warning_line_ids': [
                    (0, 0, {
                        'budgetary_position_id': line.crossovered_budget_line_id.general_budget_id.id,
                        'account_id': line.deposit_account_id.id,
                        'planned_budget': line.crossovered_budget_line_id.budget_amount,
                        'expense_budget': line.crossovered_budget_line_id.remaining_amount,
                        'realized_amount': line.amount,
                    }) for line in exceeding_lines
                ]
            })
            return {
                'name': 'Warning',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'expense.request.warning',
                'res_id': wizard.id,
                'target': 'new',
            }
        else:
            res = super(VendorDeposit, self).action_request_approval_cash_advance()
            return res