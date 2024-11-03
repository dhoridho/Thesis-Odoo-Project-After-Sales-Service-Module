from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class MonthlyAccountBudget(models.Model):
    _name = "monthly.account.budget"
    _description = 'Monthly Account Budget'

    @api.model
    def _domain_branch(self):
        return [('id','in', self.env.companies.ids)]

    account_plan_id = fields.Selection([
        ('all_account', 'All Account'),
        ('balance_sheet', 'Balance Sheet'),
        ('profit_lose', 'Profit and Loss')
    ], 'Account to plan', default='all_account')
    year = fields.Integer(string="Year", required=False)
    year_id = fields.Many2one('sh.fiscal.year', string='Fiscal Year')
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company, domain=_domain_branch,)
    name = fields.Char(string="Name")
    # year = fields.Selection (selection='years_selection',
    #     string="Year",
    #     default="2022")

    budget_account_line_ids = fields.One2many('monthly.account.budget.lines', 'monthly_budget_id',
                                              'Monthly Budget Lines')

    # def years_selection(self):
    #     year_list = []
    #     for y in range(datetime.now().year, datetime.now().year + 100):
    #         year_list.append((str(y), str(y)))
    #     return year_list

    @api.onchange('account_plan_id', 'company_id')
    def fill_lines_accounts(self):
        self.ensure_one()
        accounts_obj = self.env['account.account']
        lines = [(5, 0, 0)]
        if self.account_plan_id == 'all_account':
            all_account = accounts_obj.search([('company_id', '=', self.company_id.id)])
            for account in all_account:
                val = {
                    'account_id': account.id
                }
                lines.append((0, 0, val))
            self.budget_account_line_ids = lines

        if self.account_plan_id == 'balance_sheet':
            all_account = accounts_obj.search(
                [('user_type_id.internal_group', 'in', ['equity', 'asset', 'liability']), ('company_id', '=', self.company_id.id)])
            for account in all_account:
                val = {
                    'account_id': account.id
                }
                lines.append((0, 0, val))
            self.budget_account_line_ids = lines

        if self.account_plan_id == 'profit_lose':
            all_account = accounts_obj.search(
                [('user_type_id.internal_group', 'in', ['income', 'expense']), ('company_id', '=', self.company_id.id)])
            for account in all_account:
                val = {
                    'account_id': account.id
                }
                lines.append((0, 0, val))
            self.budget_account_line_ids = lines

class MonthlyAccountBudgetLines(models.Model):
    _name = "monthly.account.budget.lines"

    monthly_budget_id = fields.Many2one('monthly.account.budget', string='Monthly Budget')
    account_id = fields.Many2one('account.account', 'Account')  # domain="[('deprecated', '=', False)]" ,domain=lambda self: self._get_account_domain()
    jan_month = fields.Float('Jan Plan')
    feb_month = fields.Float('Feb Plan')
    march_month = fields.Float('March Plan')
    april_month = fields.Float('April Plan')
    may_month = fields.Float('May Plan')
    june_month = fields.Float('June Plan')
    july_month = fields.Float('July Plan')
    august_month = fields.Float('August Plan')
    sep_month = fields.Float('Sep Plan')
    oct_month = fields.Float('Oct Plan')
    nov_month = fields.Float('Nov Plan')
    dec_month = fields.Float('Dec Plan')
    jan_actual = fields.Float('Jan Actual', compute='_calculate_actual_for_all', store=True)
    feb_actual = fields.Float('Feb Actual', compute='_calculate_actual_for_all', store=True)
    march_actual = fields.Float('Mar Actual', compute='_calculate_actual_for_all', store=True)
    april_actual = fields.Float('April Actual', compute='_calculate_actual_for_all', store=True)
    may_actual = fields.Float('May Actual', compute='_calculate_actual_for_all', store=True)
    june_actual = fields.Float('Jun Actual', compute='_calculate_actual_for_all', store=True)
    july_actual = fields.Float('Jul Actual', compute='_calculate_actual_for_all', store=True)
    august_actual = fields.Float('Aug Actual', compute='_calculate_actual_for_all', store=True)
    sep_actual = fields.Float('Sep Actual', compute='_calculate_actual_for_all', store=True)
    oct_actual = fields.Float('Oct Actual', compute='_calculate_actual_for_all', store=True)
    nov_actual = fields.Float('Nov Actual', compute='_calculate_actual_for_all', store=True)
    dec_actual = fields.Float('Dec Actual', compute='_calculate_actual_for_all', store=True)
    planned_amount = fields.Float('Planned Amount', compute='_calculate_planned_amount', store=True)
    actual_amount = fields.Float('Actual Amount', compute='_calculate_actual_amount', store=True)
    over_budget = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Overbudget", compute='_calculate_overbudget_amount', store=True)

    @api.depends('jan_month', 'feb_month', 'march_month', 'april_month', 'may_month', 'june_month', 'july_month', 'august_month', 'sep_month', 'oct_month', 'nov_month', 'dec_month')
    def _calculate_planned_amount(self):
        for record in self:
            record.planned_amount = (record.jan_month + 
                                    record.feb_month + 
                                    record.march_month + 
                                    record.april_month + 
                                    record.may_month + 
                                    record.june_month + 
                                    record.july_month + 
                                    record.august_month + 
                                    record.sep_month + 
                                    record.oct_month + 
                                    record.nov_month + 
                                    record.dec_month
                                )
    
    @api.depends('jan_actual', 'feb_actual', 'march_actual', 'april_actual', 'may_actual', 'june_actual', 'july_actual', 'august_actual', 'sep_actual', 'oct_actual', 'nov_actual', 'dec_actual')
    def _calculate_actual_amount(self):
        for record in self:
            record.actual_amount = (record.jan_actual + 
                                    record.feb_actual + 
                                    record.march_actual + 
                                    record.april_actual + 
                                    record.may_actual + 
                                    record.june_actual + 
                                    record.july_actual + 
                                    record.august_actual + 
                                    record.sep_actual + 
                                    record.oct_actual + 
                                    record.nov_actual + 
                                    record.dec_actual
                                )

    @api.depends('planned_amount', 'actual_amount')
    def _calculate_overbudget_amount(self):
        for record in self:
            over_budget = (record.planned_amount - record.actual_amount)
            if record.planned_amount < 0 and record.actual_amount < 0:
                if record.actual_amount < record.planned_amount:
                    record.over_budget = 'yes' 
                else:
                    record.over_budget = 'no'
            else:
                if over_budget > 0:
                    record.over_budget = 'no'
                else:
                    record.over_budget = 'yes'

    @api.onchange('account_id')
    def _get_account_domain(self):
        res = "[('deprecated', '=', False)]"
        for record in self:
            if record.monthly_budget_id.account_plan_id == 'all_account':
                res = {
                    'domain': {
                        'account_id': "[('user_type_id.internal_group', 'in', ['equity','asset','liability','income','expense'])]"
                    }
                }

            if record.monthly_budget_id.account_plan_id == 'balance_sheet':
                res = {
                    'domain': {
                        'account_id': "[('user_type_id.internal_group', 'in', ['equity','asset','liability'])]"
                    }
                }

            if record.monthly_budget_id.account_plan_id == 'profit_lose':
                res = {
                    'domain': {
                        'account_id': "[('user_type_id.internal_group', 'in', ['income','expense'])]"
                    }
                }

        return res

    @api.depends('monthly_budget_id.account_plan_id', 'account_id', 'monthly_budget_id.year_id')
    def _calculate_actual_for_all(self):
        for record in self:
            record.jan_actual = 0
            record.feb_actual = 0
            record.march_actual = 0
            record.april_actual = 0
            record.may_actual = 0 
            record.june_actual = 0
            record.july_actual = 0
            record.august_actual = 0
            record.sep_actual = 0
            record.oct_actual = 0
            record.nov_actual = 0
            record.dec_actual = 0
            year_start = date.today().replace(day=1, month=1)
            year_end = date.today().replace(day=31, month=12)
            if record.monthly_budget_id.year_id:
                year_start = record.monthly_budget_id.year_id.date_start
                year_end = record.monthly_budget_id.year_id.date_end
            move_line_ids = self.env['account.move.line'].read_group(
                domain=[('date', '>=', year_start), ('date', '<=', year_end), ('account_id', '=', record.account_id.id)],
                fields=['debit', 'credit'],
                groupby='date:month'
            )
            for data in move_line_ids:
                if data.get('date:month').startswith('January'):
                    debit_jan = data.get('debit')
                    credit_jan = data.get('credit')
                    total_balance_jan = debit_jan - credit_jan
                    record.jan_actual = total_balance_jan
                if data.get('date:month').startswith('February'):
                    debit_feb = data.get('debit')
                    credit_feb = data.get('credit')
                    total_balance_feb = debit_feb - credit_feb
                    record.feb_actual = total_balance_feb
                if data.get('date:month').startswith('March'):
                    debit_mar = data.get('debit')
                    credit_mar = data.get('credit')
                    total_balance_mar = debit_mar - credit_mar
                    record.march_actual = total_balance_mar
                if data.get('date:month').startswith('April'):
                    debit_apr = data.get('debit')
                    credit_apr = data.get('credit')
                    total_balance_apr = debit_apr - credit_apr
                    record.april_actual = total_balance_apr
                if data.get('date:month').startswith('May'):
                    debit_may = data.get('debit')
                    credit_may = data.get('credit')
                    total_balance_may = debit_may - credit_may
                    record.may_actual = total_balance_may
                if data.get('date:month').startswith('June'):
                    debit_jun = data.get('debit')
                    credit_jun = data.get('credit')
                    total_balance_jun = debit_jun - credit_jun
                    record.june_actual = total_balance_jun
                if data.get('date:month').startswith('July'):
                    debit_jul = data.get('debit')
                    credit_jul = data.get('credit')
                    total_balance_jul = debit_jul - credit_jul
                    record.july_actual = total_balance_jul
                if data.get('date:month').startswith('August'):
                    debit_aug = data.get('debit')
                    credit_aug = data.get('credit')
                    total_balance_aug = debit_aug - credit_aug
                    record.august_actual = total_balance_aug
                if data.get('date:month').startswith('September'):
                    debit_sep = data.get('debit')
                    credit_sep = data.get('credit')
                    total_balance_sep = debit_sep - credit_sep
                    record.sep_actual = total_balance_sep
                if data.get('date:month').startswith('October'):
                    debit_oct = data.get('debit')
                    credit_oct = data.get('credit')
                    total_balance_oct = debit_oct - credit_oct
                    record.oct_actual = total_balance_oct
                if data.get('date:month').startswith('November'):
                    debit_nov = data.get('debit')
                    credit_nov = data.get('credit')
                    total_balance_nov = debit_nov - credit_nov
                    record.nov_actual = total_balance_nov
                if data.get('date:month').startswith('December'):
                    debit_dec = data.get('debit')
                    credit_dec = data.get('credit')
                    total_balance_dec = debit_dec - credit_dec
                    record.dec_actual = total_balance_dec

