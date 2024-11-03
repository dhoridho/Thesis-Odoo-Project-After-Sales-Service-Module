from ast import Store
import json
from datetime import datetime
from re import L
import sre_compile
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class BudgetScurve(models.TransientModel):
    _name = 'budget.scurve'  
    
    name = fields.Char(string='Name')
    budget_to_analyze  = fields.Selection([
    ('budget', 'Budget'),
    ('purchase_budget', 'Purchase Budget'),
    ('account_budget', 'Account Budget')
    ], 'Budget to Analyze', default='budget', index=True, required=True)
    crossovered_budget = fields.Many2one("crossovered.budget", string="Crossovered Budget")
    
    budgetary_position = fields.Many2many("budgetary.position", string="Budgetory Position")
    period_start_date  = fields.Many2one("crossovered.budget", string="Start Date")
    period_end_date  = fields.Many2one("crossovered.budget", string="End Date")

    crossovered_purchase_budget = fields.Many2one("budget.purchase ", string="Purchase Budget Name")
    product_purchase_budget = fields.Many2many("product.template", string="Product")

    crossovered_acount_budget = fields.Many2one("account.budget", string="Account Budget Name")
    acount_account_budget = fields.Many2many("account.account", string="Account")



    project_id = fields.Many2one("project.project", string="Project")
    job_cost_sheet = fields.Many2one('job.cost.sheet', 'Cost Sheet')
    work_orders_ids = fields.Many2many("project.task", 'budget_scurve_work_order_rel', 'budget_id', 'work_order_id', string="Work Orders")
    account_tag_ids = fields.Many2many("account.tag_ids",'budget_scurve_account_analytic_tags_rel', 'budget_id', 'analytic_tag_id', string="Analytic Groups")
    

    start_date = fields.Date(string=_('Start Date'), required=True, tracking=True)
    end_date = fields.Date(string=_('End Date'), required=True, tracking=True)
    contract_amount = fields.Float(string='Contract Amount')
    method = fields.Selection([('cost','Plan vs Actual Cost'),('progress','Plan vs Actual Progress'), ('cvp', 'Cost Progress'), ('pa_costprog', 'Plan and Actual Cost vs Progress')], string = "Method", default='cost')
    ks_chart_data = fields.Text(string=_("Chart Data"), default={
        'labels': name,
        'datasets': [{
            'data' : []
    }]})
    ks_graph_view = fields.Integer(string="Graph view", default=1)   
    crossovered_budget_line_ids = fields.Many2many("crossovered.budget.lines", 'budget_scurve_crossovered_lines_rel', 'corssovered_budget_line_id', 'scurve_budget_id', string="Crossovered Budget Lines")
    purchase_budget_line_ids = fields.Many2many("budget.purchase.lines", 'budget_scurve_purchase_lines_rel', 'purchase_budget_line_id', 'scurve_budget_id', string="Purchase Budget Lines")
    acount_account_budget_ids = fields.Many2many("monthly.account.budget.lines", 'budget_scurve_account_lines_rel', 'account_budget_line_id', 'scurve_budget_id', string="Account Budget Lines")
    

    crossovered_budget_line_count = fields.Integer(string='Budget Count', compute='_compute_crossovered_line_count', store=True)
    from_menu = fields.Boolean('Is Orders', default=False)
    budget_scurve_line_ids = fields.One2many(comodel_name='budget.scurve.line', inverse_name='scurve_id', string='Scurve Line')
    
    def scurve_create_data_dict(self,result):
        data_dict = {}
        for data in result:
            keys = data_dict.keys()
            project_data = {
                'ks_scurve_id': self.id,
                'ks_value': float(self.crossovered_budget_line_count),
                'ks_crossovered_budget': self.crossovered_budget.id,
                'ks_company__id': self.crossovered_budget.company_id.id,
            }
            if self.crossovered_budget.id in keys:
                data_dict[self.crossovered_budget.id]['project'].append(self.crossovered_budget.name)
                data_dict[self.crossovered_budget.id]['count'].append(self.crossovered_budget_line_count)
            else:
                data_dict[self.crossovered_budget.id] = {'project': [], 'count': []}
        return data_dict

    def get_labels(self):
        if self.method == 'cost':
            name = 'amount'
        else:
            name = 'progress(%)'
        return name

    def get_month(self):
        start_date = datetime.strptime(str(self.start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.end_date), "%Y-%m-%d")
        month = []
        for res in self:
            if res.end_date:
                while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                    end_date = start_date + relativedelta(months=+1, days=-1)
                    year_date = start_date.strftime("%Y")
                    month_date = start_date.strftime("%B")
                    month_year = month_date + ' ' + year_date

                    if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                        end_date = ends_date

                    month.append(month_year)
                    start_date = start_date + relativedelta(months=+1)
        return month

    def get_planned_cost_table(self):
        planned = []
        line = []
        planned_amount = 0.0
        start_date = datetime.strptime(str(self.start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.end_date), "%Y-%m-%d")
        if self.method == 'cost':
            self.budget_scurve_line_ids = [(5, 0, 0)]
        if self.budget_to_analyze:
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                line = []
                end_date = start_date + relativedelta(months=+1, days=-1)
                month_date = start_date.strftime("%B")
                year_date = start_date.strftime("%Y")
                # budget = self.env['project.budget'].search([('project_id', '=', self.project_id.id), ('month.month', '=', month_date), ('month.year', '=', year_date)])
                if self.budget_to_analyze == 'budget':
                    budget_lines = self.env['crossovered.budget.lines'].search([('crossovered_budget_id', '=', self.crossovered_budget.id),('date_from', '>=', start_date), ('date_to', '=', ends_date)])
                    total_crossovered = 0
                    for budget_cross in budget_lines:
                        total_crossovered += budget_cross.planned_amount
                    planned_amount = total_crossovered
                elif self.budget_to_analyze == 'purchase_budget':
                    budget_lines = self.env['budget.purchase.lines'].search([('purchase_budget_id', '=', self.crossovered_purchase_budget.id),('date_from', '>=', start_date), ('date_to', '=', ends_date)])
                    total_budget = 0
                    for budget in budget_lines:
                        total_budget += budget.planned_amount
                    planned_amount = total_budget
                else:
                    budget_lines = self.env['monthly.account.budget.lines'].search([('monthly_budget_id', '=', self.crossovered_acount_budget.id), ('account_id','in',self.acount_account_budget.ids)])
                    if month_date == 'January':
                        jan_month = 0
                        for budget in budget_lines:
                            jan_month += budget.jan_month
                        planned_amount = jan_month
                    elif month_date == 'February':
                        feb_month = 0
                        for budget in budget_lines:
                            feb_month += budget.feb_month
                        planned_amount = feb_month
                    elif month_date == 'March':
                        march_month = 0
                        for budget in budget_lines:
                            march_month += budget.march_month
                        planned_amount = march_month
                    elif month_date == 'April':
                        april_month = 0
                        for budget in budget_lines:
                            april_month += budget.april_month
                        planned_amount = april_month
                    elif month_date == 'May':
                        may_month = 0
                        for budget in budget_lines:
                            may_month += budget.may_month
                        planned_amount = may_month
                    elif month_date == 'June':
                        june_month = 0
                        for budget in budget_lines:
                            june_month += budget.june_month
                        planned_amount = june_month
                    elif month_date == 'July':
                        july_month = 0
                        for budget in budget_lines:
                            july_month += budget.july_month
                        planned_amount = july_month
                    elif month_date == 'August':
                        august_month = 0
                        for budget in budget_lines:
                            august_month += budget.august_month
                        planned_amount = august_month
                    
                    elif month_date == 'September':
                        sep_month = 0
                        for budget in budget_lines:
                            sep_month += budget.sep_month
                        planned_amount = sep_month
                    elif month_date == 'October':
                        oct_month = 0
                        for budget in budget_lines:
                            oct_month += budget.oct_month
                        planned_amount = oct_month
                    elif month_date == 'November':
                        nov_month = 0
                        for budget in budget_lines:
                            nov_month += budget.nov_month
                        planned_amount = nov_month
                    elif month_date == 'December':
                        dec_month = 0
                        for budget in budget_lines:
                            dec_month += budget.dec_month
                        planned_amount = dec_month
                      


                line_src = self.env['budget.scurve.line'].search([('scurve_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                        
                if budget_lines:
                    if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                            end_date = ends_date
                elif line_src:
                    self.budget_scurve_line_ids = [(1, line_src.id, {
                                'planned_amount': planned_amount,
                            })]
                else:
                    return planned
                
                if line_src:
                    self.budget_scurve_line_ids = [(1, line_src.id, {
                                'planned_amount': planned_amount,
                            })]
                else:
                    line.append((0, 0, {
                        'scurve_id': self.id,
                        'month': month_date,
                        'year': year_date,
                        'planned_amount': planned_amount,
                    }))

                self.budget_scurve_line_ids = line
                start_date = start_date + relativedelta(months=+1)
            
        
    



    def get_actual_cost_table(self):
        actual = []
        amount = 0.0
        start_date = datetime.strptime(str(self.start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.end_date), "%Y-%m-%d")
        if self.budget_to_analyze:
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                end_date = start_date + relativedelta(months=+1, days=-1)
                month_date = start_date.strftime("%B")
                year_date = start_date.strftime("%Y")
                # budget = self.env['project.budget'].search([('project_id', '=', self.project_id.id), ('month.month', '=', month_date), ('month.year', '=', year_date)])
                # line_src = self.env['budget.scurve.line'].search([('scurve_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                line_src = self.env['budget.scurve.line'].search([('scurve_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                if self.budget_to_analyze == 'budget':
                    budget_lines = self.env['crossovered.budget.lines'].search([('crossovered_budget_id', '=', self.crossovered_budget.id),('date_from', '>=', start_date), ('date_to', '=', ends_date)])
                    for b_line in budget_lines:
                        amount += b_line.practical_budget_amount

                elif self.budget_to_analyze == 'purchase_budget':
                    budget_lines = self.env['budget.purchase.lines'].search([('purchase_budget_id', '=', self.crossovered_purchase_budget.id),('date_from', '>=', start_date), ('date_to', '=', ends_date)])
                    for b_line in budget_lines:
                        amount += b_line.practical_amount

                else:
                    budget_lines = self.env['monthly.account.budget.lines'].search([('monthly_budget_id', '=', self.crossovered_acount_budget.id), ('account_id','in',self.acount_account_budget.ids)])
                    if month_date == 'January':
                        jan_actual = 0
                        for budget in budget_lines:
                            jan_actual += budget.jan_actual
                        amount = jan_actual
                    elif month_date == 'February':
                        feb_actual = 0
                        for budget in budget_lines:
                            feb_actual += budget.feb_actual
                        amount = feb_actual
                    elif month_date == 'March':
                        march_actual = 0
                        for budget in budget_lines:
                            march_actual += budget.march_actual
                        amount = march_actual
                    elif month_date == 'April':
                        april_actual = 0
                        for budget in budget_lines:
                            april_actual += budget.april_actual
                        amount = april_actual
                    elif month_date == 'May':
                        may_actual = 0
                        for budget in budget_lines:
                            may_actual += budget.may_actual
                        amount = may_actual
                    elif month_date == 'June':
                        june_actual = 0
                        for budget in budget_lines:
                            june_actual += budget.june_actual
                        amount = june_actual
                    elif month_date == 'July':
                        july_actual = 0
                        for budget in budget_lines:
                            july_actual += budget.july_actual
                        amount = july_actual
                    elif month_date == 'August':
                        august_actual = 0
                        for budget in budget_lines:
                            august_actual += budget.august_actual
                        amount = august_actual
                    
                    elif month_date == 'September':
                        sep_actual = 0
                        for budget in budget_lines:
                            sep_actual += budget.sep_actual
                        amount = sep_actual
                    elif month_date == 'October':
                        oct_actual = 0
                        for budget in budget_lines:
                            oct_actual += budget.oct_actual
                        amount = oct_actual
                        
                    elif month_date == 'November':
                        nov_actual = 0
                        for budget in budget_lines:
                            nov_actual += budget.nov_actual
                        amount = nov_actual
                    elif month_date == 'December':
                        dec_actual = 0
                        for budget in budget_lines:
                            dec_actual += budget.dec_actual
                        amount = dec_actual
                      



                    print (month_date, 'month_date')


                if budget_lines:
                    if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                            end_date = ends_date
                else:
                    return actual
                
                self.budget_scurve_line_ids = [(1, line_src.id, {
                            'actual_cost': amount,
                        })]
                start_date = start_date + relativedelta(months=+1)
            else:
                pass

    



    def get_plan_cost_from_table(self):
        planned = []
        cost = 0.0
        if self.budget_scurve_line_ids:
            for line in self.budget_scurve_line_ids:
                cost = line.planned_amount
                planned.append(cost)
            return planned
    
    def get_plan_progress_from_table(self):
        planned = []
        acc_progress = 0.0
        if self.budget_scurve_line_ids:
            for line in self.budget_scurve_line_ids:
                prog = line.planned_progress
                acc_progress = prog
                planned.append(acc_progress)
            return planned

    def get_actual_cost_from_table(self):
        actual = []
        acc_progress = 0.0
        if self.budget_scurve_line_ids:
            for line in self.budget_scurve_line_ids:
                acc_progress = line.actual_cost
                actual.append(acc_progress)
            return actual

    def get_actual_progress_from_table(self):
        actual = []
        acc_progress = 0.0
        if self.budget_scurve_line_ids:
            for line in self.budget_scurve_line_ids:
                prog = line.actual_progress
                acc_progress = prog
                actual.append(acc_progress)
            return actual
    
    def get_plan_cost_progress_from_table(self):
        planned = []
        cost = 0.0
        if self.budget_scurve_line_ids:
            for line in self.budget_scurve_line_ids:
                prog = line.prog_planned_cost
                cost = prog
                planned.append(cost)
            return planned
    
    def get_actual_cost_progress_from_table(self):
        actual = []
        acc_progress = 0.0
        if self.budget_scurve_line_ids:
            for line in self.budget_scurve_line_ids:
                prog = line.prog_actual_cost
                acc_progress = prog
                actual.append(acc_progress)
            return actual
    
    def create_scurve(self, final_dict):
        final_dict = {}
        month = self.get_month()
        label_1 = ''
        label_2 = ''
        
        # planned = self.get_planned()
        # actual = self.get_actual()
        # self.get_labels()

        if self.method == 'cost':
            name = self.get_labels()
            self.get_planned_cost_table()
            self.get_actual_cost_table()
            planned = self.get_plan_cost_from_table()
            actual = self.get_actual_cost_from_table()
            label_1 = 'Planned '
            label_2 = 'Practical '
            name1 = name
            name2 = name
        
        
        
        if self.method == 'pa_costprog': 
            final_dict.update({
                'labels': month,
                'datasets': [{
                    'data' : planned,
                    'label': label_1 + name1,
                    }, {
                    'data' : planned1,
                    'label': label_1 + name2,
                    }, {
                    'data' : actual,
                    'label': label_2 + name1,
                    }, {
                    'data': actual1,
                    'label': label_2 + name2,
                    }]
                })
            self.ks_chart_data = json.dumps(final_dict)
            print(final_dict)
            return final_dict
        else:
            final_dict.update({
                'labels': month,
                'datasets': [{
                    'data' : planned,
                    'label': label_1 + name1,
                    }, {
                    'data': actual,
                    'label': label_2 + name2,
                    }]
                })
            self.ks_chart_data = json.dumps(final_dict)
            print(final_dict)
            return final_dict

    @api.depends('crossovered_budget_line_ids','purchase_budget_line_ids', 'method')
    def _compute_crossovered_line_count(self):
        for record in self:
            if record.method == 'budget':
                record.crossovered_budget_line_count = len(record.crossovered_budget_line_ids.ids) 
            elif record.method == 'purchase_budget' :
                record.crossovered_budget_line_count = len(record.purchase_budget_line_ids.ids) 
            else:
                record.crossovered_budget_line_count = len(record.acount_account_budget_ids.ids) 
            
        data =  self.scurve_create_data_dict(self.project_id)
        self.create_scurve(data)

    
    def cons_scurve_print(self):
        pass

class BudgetScurveLine(models.TransientModel):
    _name = 'budget.scurve.line'
    _description = "Budget Scurve Line"

    scurve_id = fields.Many2one(comodel_name='budget.scurve', string='Scurve Line')
    # cs_id = fields.Many2one('job.cost.sheet', 'CS ID')
    # cs_material_id = fields.Many2one('material.material', 'CS Material ID')
    # cs_labour_id = fields.Many2one('material.labour', 'CS Labour ID')
    # cs_overhead_id = fields.Many2one('material.overhead', 'CS Overhead ID')
    # cs_equipment_id = fields.Many2one('material.equipment', 'CS Equipment ID')
    # # bd_id = fields.Many2many(comodel_name='project.budget', string='Project Budget')
    # bd_material_id = fields.Many2many('budget.material', 'BD Material ID')
    # bd_labour_id = fields.Many2many('budget.labour', 'BD Labour ID')
    # bd_overhead_id = fields.Many2many('budget.overhead', 'BD Overhead ID')
    # bd_equipment_id = fields.Many2many('budget.equipment', 'BD Overhead ID')
    # work_orders_line_ids = fields.Many2many("project.task", string="Work Orders")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    month = fields.Char(string='Month')
    year = fields.Char(string='Year')
    planned_cost = fields.Float(string='Planned Cost')
    planned_amount = fields.Float(string='Planned Cost')
    
    actual_cost = fields.Float(string='Practical Cost')

    prog_planned_cost = fields.Float(string='Progress Planned Cost')
    prog_actual_cost = fields.Float(string='Progress Actual Cost')
    contract_amount = fields.Float(string='Contract Amount', related='scurve_id.contract_amount')
    planned_progress = fields.Float(string='Planned Progress')
    actual_progress = fields.Float(string='Actual Progress')
    planned_revenue = fields.Float(string='Planned Revenue')
    actual_revenue = fields.Float(string='Actual Revenue')
    planned_material_cost = fields.Float(string='Planned Material Cost')
    actual_material_cost = fields.Float(string='Actual Material Cost')
    method = fields.Selection([
        ('cost', 'Cost'),
        ('progress', 'Progress')
    ], string='Method', related='scurve_id.method')

    def _compute_plan_cost_progress(self):
        for line in self:
            cost = line.planned_amount / line.contract_amount * 100
            line.prog_planned_cost = cost

    def _compute_actual_cost_progress(self):
        for line in self:
            cost = line.actual_cost / line.contract_amount * 100
            line.prog_actual_cost = cost
            

    @api.depends('scurve_id.budget_scurve_line_ids', 'scurve_id.budget_scurve_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.scurve_id.budget_scurve_line_ids:
                no += 1
                l.sr_no = no