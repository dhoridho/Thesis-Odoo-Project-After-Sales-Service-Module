
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"


    is_from_receiving_note = fields.Boolean('Is From Receiving Note', default=False)

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for record in self:
            if record.move_type == "entry":
                monthly_account_budget_id = self.env['monthly.account.budget'].search([
                    ('year_id', '=', record.fiscal_year.id),
                    ('company_id', '=', record.company_id.id),
                    ], limit=1)
                monthly_account_budget_id.budget_account_line_ids._calculate_actual_for_all()
        return res

    # def action_confirm(self):
    #     exceeding_lines = self.check_overbudget()
    #     if exceeding_lines:
    #         wizard = self.env['expense.request.warning'].create({
    #             'warning_line_ids': [
    #                 (0, 0, {
    #                     'budgetary_position_id': line.crossovered_budget_line_id.general_budget_id.id,
    #                     'account_id': line.account_id.id,
    #                     'planned_budget': line.crossovered_budget_line_id.budget_amount,
    #                     'expense_budget': line.crossovered_budget_line_id.remaining_amount,
    #                     'realized_amount': line.amount_currency,
    #                 }) for line in exceeding_lines
    #             ]
    #         })
    #         return {
    #             'name': 'Warning',
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'form',
    #             'res_model': 'expense.request.warning',
    #             'res_id': wizard.id,
    #             'target': 'new',
    #         }
    #     else:
    #         res = super(AccountMove, self).action_confirm()
    #         return res

    # def action_request_for_approval(self):
    #     exceeding_lines = self.check_overbudget()
    #     if exceeding_lines:
    #         wizard = self.env['expense.request.warning'].create({
    #             'warning_line_ids': [
    #                 (0, 0, {
    #                     'budgetary_position_id': line.crossovered_budget_line_id.general_budget_id.id,
    #                     'account_id': line.account_id.id,
    #                     'planned_budget': line.crossovered_budget_line_id.budget_amount,
    #                     'expense_budget': line.crossovered_budget_line_id.remaining_amount,
    #                     'realized_amount': line.amount_currency,
    #                 }) for line in exceeding_lines
    #             ]
    #         })
    #         return {
    #             'name': 'Warning',
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'form',
    #             'res_model': 'expense.request.warning',
    #             'res_id': wizard.id,
    #             'target': 'new',
    #         }
    #     else:
    #         res = super(AccountMove, self).action_request_for_approval()
    #         return res

    def check_overbudget(self):
        exceeding_lines = []
        for record in self:
            for line in record.line_ids:
                if line.crossovered_budget_line_id:
                    subtotal_cost_same_budget = 0
                    for line2 in record.line_ids:
                        if line2.crossovered_budget_line_id.id == line.crossovered_budget_line_id.id:
                            subtotal_cost_same_budget += line2.amount_currency

                    if subtotal_cost_same_budget > line.crossovered_budget_line_id.remaining_amount:
                        exceeding_lines.append(line)

        return exceeding_lines


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    crossovered_budget_line_id = fields.Many2one('crossovered.budget.lines', string='Budget Line', compute='_get_crossovered_budget_line', store=True)
    crossovered_budget_id = fields.Many2one('crossovered.budget', related='crossovered_budget_line_id.crossovered_budget_id')
    general_budget_id = fields.Many2one('account.budget.post', string='Budgetary Position')

    @api.depends('date','account_id','analytic_tag_ids')
    def _get_crossovered_budget_line(self):
        for line in self:
            line.crossovered_budget_line_id = False
            budget_lines = self.env['crossovered.budget.lines'].search([
                ('crossovered_budget_id.state', '=', 'validate'),
                ('date_from', '<=', line.date), 
                ('date_to', '>=', line.date),
            ])
            for budget in budget_lines:
                acc_ids = budget.general_budget_id.account_ids.ids
                if line.account_id.id in acc_ids and any(item in line.analytic_tag_ids.ids for item in budget.account_tag_ids.ids):
                    line.crossovered_budget_line_id = budget.id
                    line.general_budget_id = budget.general_budget_id.id