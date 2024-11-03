from odoo import _, api, fields, models
from datetime import datetime

class SCurveBudget(models.TransientModel):
    _name = "s.curve.budget"
    _description = "S-Curve"

    budget_to_analyze  = fields.Selection([
    ('budget', 'Budget'),
    ('purchase_budget', 'Purchase Budget'),
    ('account_budget', 'Account Budget')
    ], 'Budget to Analyze', default='budget', index=True, required=True)

    crossovered_budget = fields.Many2one("crossovered.budget", string="Crossovered Budget")
    
    budgetary_position = fields.Many2many("account.budget.post", string="Budgetory Position")
    period_start_date  = fields.Date(string="Start Date")
    period_end_date  = fields.Date(string="End Date")

    crossovered_purchase_budget = fields.Many2one("budget.purchase", string="Purchase Budget Name")
    crossovered_purchase_budget_parent_id = fields.Many2one('crossovered.budget', 'Budget Account Reference', related='crossovered_purchase_budget.parent_id')

    product_purchase_budget = fields.Many2many("product.product", string="Product")
    group_product_purchase_budget = fields.Many2many('account.product.group', string="Group of Product")

    crossovered_acount_budget = fields.Many2one("monthly.account.budget", string="Account Budget Name")
    acount_account_budget = fields.Many2many("account.account", string="Account")


    @api.onchange('budget_to_analyze', 'crossovered_budget')
    def get_workorder(self):
        for res in self:
            budget_lines = res.env['crossovered.budget.lines'].search([('crossovered_budget_id', '=', self.crossovered_budget.id)])
            budgetory_position = []
            for budget_line in budget_lines:
                budgetory_position.append(budget_line.general_budget_id.id)
            res.budgetary_position = [(6, 0, budgetory_position)]
            res.period_start_date = res.crossovered_budget.date_from
            res.period_end_date = res.crossovered_budget.date_to

    @api.onchange('budget_to_analyze', 'crossovered_acount_budget')
    def get_crossovered_acount_budget(self):
        for res in self:
            if res.crossovered_acount_budget:
                budget_lines = res.env['monthly.account.budget.lines'].search([('monthly_budget_id', '=', self.crossovered_acount_budget.id)])
                budgetory_position = []
                for budget_line in budget_lines:
                    budgetory_position.append(budget_line.account_id.id)
                res.acount_account_budget = [(6, 0, budgetory_position)]
                res.period_start_date = fields.Date.today().strftime('%Y-01-01')
                res.period_end_date = fields.Date.today().strftime('%Y-12-31')

    @api.onchange('budget_to_analyze', 'crossovered_purchase_budget')
    def get_crossovered_purchase_budget(self):
        for res in self:
            if res.crossovered_purchase_budget:
                budget_lines = res.env['budget.purchase.lines'].search([('purchase_budget_id', '=', self.crossovered_purchase_budget.id)])
                budgetory_position = []
                group_products = []
                product_budgets = []
                for budget_line in budget_lines:
                    if budget_line.product_id:
                        budgetory_position.append(budget_line.product_id.id)
                    if budget_line.group_product_id:
                        group_products.append(budget_line.group_product_id.id)
                    if budget_line.product_budget:
                        product_budgets.append(budget_line.product_budget.id)
                res.product_purchase_budget = [(6, 0, budgetory_position)]
                res.group_product_purchase_budget = [(6, 0, group_products)]
                res.budgetary_position = [(6, 0, product_budgets)]
                res.period_start_date = res.crossovered_purchase_budget.date_from
                res.period_end_date = res.crossovered_purchase_budget.date_to


            

    def create_scurve(self):
        for res in self:
            if res.budget_to_analyze == 'budget':
                self.env['budget.scurve'].create({
                    'name': res.crossovered_budget.name,
                    'budget_to_analyze': res.budget_to_analyze,
                    'crossovered_budget': res.crossovered_budget.id,
                    'start_date': res.period_start_date,
                    'end_date': res.period_end_date,
                    # 'job_cost_sheet': res.project.cost_sheet.id,
                    # 'project_budget': bud,
                    # 'contract_amount': res.project.total_estimation_cost,
                    'account_tag_ids': [(6, 0, res.crossovered_budget.account_tag_ids.ids)],
                    'crossovered_budget_line_ids': [(6, 0, res.crossovered_budget.crossovered_budget_line.ids)],
                      
                })
            elif res.budget_to_analyze == 'purchase_budget':
                self.env['budget.scurve'].create({
                    'name': res.crossovered_purchase_budget.name,
                    'budget_to_analyze': res.budget_to_analyze,
                    'crossovered_purchase_budget': res.crossovered_purchase_budget.id,
                    'start_date': res.period_start_date,
                    'end_date': res.period_end_date,
                    # 'job_cost_sheet': res.project.cost_sheet.id,
                    # 'project_budget': bud,
                    # 'contract_amount': res.project.total_estimation_cost,
                    'account_tag_ids': [(6, 0, res.crossovered_purchase_budget.account_tag_ids.ids)],
                    'purchase_budget_line_ids': [(6, 0, res.crossovered_purchase_budget.purchase_budget_line.ids)],
                      
                })
            else:
                self.env['budget.scurve'].create({
                    'name': res.crossovered_acount_budget.name,
                    'budget_to_analyze': res.budget_to_analyze,
                    'crossovered_acount_budget': res.crossovered_acount_budget.id,
                    'start_date': res.period_start_date,
                    'end_date': res.period_end_date,
                    'acount_account_budget': [(6, 0, res.acount_account_budget.ids)],
                    # 'job_cost_sheet': res.project.cost_sheet.id,
                    # 'project_budget': bud,
                    # 'contract_amount': res.project.total_estimation_cost,
                    'acount_account_budget_ids': [(6, 0, res.crossovered_acount_budget.budget_account_line_ids.ids)],
                      
                })

        scurve_id = self.env['budget.scurve'].search([], limit = 1, order = 'id desc')
        return scurve_id.get_formview_action()