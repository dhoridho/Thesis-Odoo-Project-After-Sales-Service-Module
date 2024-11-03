# -*- coding: utf-8 -*-
from odoo import fields, models


class MonthlyAccountBudgetLines(models.Model):
    _inherit = "monthly.account.budget.lines"

    account_plan_id = fields.Selection(related='monthly_budget_id.account_plan_id', string='Account to Plan', store=True)
    year_id = fields.Many2one('sh.fiscal.year', related='monthly_budget_id.year_id', string='Fiscal Year', store=True)
    year_name = fields.Char(related='monthly_budget_id.year_id.name', string='Fiscal Year Name', store=True)
    date_start = fields.Date(related='monthly_budget_id.year_id.date_start', string='Start Date', store=True)
    date_end = fields.Date(related='monthly_budget_id.year_id.date_end', string='End Date', store=True)
