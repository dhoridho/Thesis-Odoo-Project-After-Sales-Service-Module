import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

from odoo import api, fields, models, _


class Scurve(models.TransientModel):
    _name = 'construction.scurve'
    _description = "Construction Scurve"
    
    name = fields.Char(string='Name')
    project_id = fields.Many2one("project.project", string="Project", domain="[('primary_states','=', ('progress', 'completed'))]")
    job_cost_sheet = fields.Many2one('job.cost.sheet', 'Cost Sheet')
    project_budget = fields.Many2many(comodel_name='project.budget', string='Project Budget')
    work_orders_ids = fields.Many2many("project.task", string="Work Orders")
    start_date = fields.Date(string=_('Start Date'), required=True)
    end_date = fields.Date(string=_('End Date'), required=True)
    contract_amount = fields.Float(string='Contract Amount')
    method = fields.Selection([('cost','Plan vs Actual Cost'),('progress','Plan vs Actual Progress'), ('cvp', 'Cost Progress'), ('pa_costprog', 'Plan and Actual Cost vs Progress'), ('all', 'Purchased vs Transferred vs Used Budget')], string = "Method", default='pa_costprog')
    ks_chart_data = fields.Text(string=_("Chart Data"), default={
        'labels': name,
        'datasets': [{
            'data' : []
    }]})
    ks_graph_view = fields.Integer(string="Graph view", default=1)   
    work_order_count = fields.Integer(string='Work Order Count', compute='_compute_work_order_count', store=True)
    from_menu = fields.Boolean('Is Orders', default=False)
    scurve_line_ids = fields.One2many(comodel_name='scurve.line', inverse_name='scurve_id', string='Scurve Line')
    
    def scurve_create_data_dict(self,result):
        data_dict = {}
        for data in result:
            keys = data_dict.keys()
            project_data = {
                'ks_scurve_id': self.id,
                'ks_value': float(self.work_order_count),
                'ks_project_id': self.project_id.id,
                'ks_partner_id': self.project_id.partner_id.id,
            }
            if self.project_id.id in keys:
                data_dict[self.project_id.id]['project'].append(self.project_id.name)
                data_dict[self.project_id.id]['count'].append(self.work_order_count)
            else:
                data_dict[self.project_id.id] = {'project': [], 'count': []}
        return data_dict

    def get_labels(self):
        if self.method == 'cost' or self.method == 'all':
            name = 'cost'
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
        cost = 0.0
        tra = 0.0
        pur = 0.0
        use = 0.0
        start_date = datetime.strptime(str(self.start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.end_date), "%Y-%m-%d")
        if self.method == 'cost':
            self.scurve_line_ids = [(5, 0, 0)]
        if self.project_budget:
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                line = []
                end_date = start_date + relativedelta(months=+1, days=-1)
                month_date = start_date.strftime("%B")
                year_date = start_date.strftime("%Y")
                budget = self.env['project.budget'].search([('project_id', '=', self.project_id.id), ('month.month', '=', month_date), ('month.year', '=', year_date)])
                line_src = self.env['scurve.line'].search([('scurve_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                cost += budget.budget_amount_total
                tra += budget.transferred_amount_total
                pur += budget.purchased_amount_total
                use += budget.actual_amount_total

                if line_src:
                    self.scurve_line_ids = [(1, line_src.id, {
                                'planned_cost': cost,
                                'purchased_amt': pur,
                                'transferred_amt': tra,
                                'used_amt': use
                            })]
                else:
                    line.append((0, 0, {
                        'scurve_id': self.id,
                        'month': month_date,
                        'year': year_date,
                        'planned_cost': cost,
                        'purchased_amt': pur,
                        'transferred_amt': tra,
                        'used_amt': use
                    }))

                self.scurve_line_ids = line
                start_date = start_date + relativedelta(months=+1)

        else:
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                line = []
                end_date = start_date + relativedelta(months=+1, days=-1)
                year_date = start_date.strftime("%Y")
                month_date = start_date.strftime("%B")
                line_src = self.env['scurve.line'].search([('scurve_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                    end_date = ends_date

                if line_src:
                    self.scurve_line_ids = [(1, line_src.id, {
                                'planned_cost': self.job_cost_sheet.amount_total,
                                'purchased_amt': self.job_cost_sheet.contract_budget_pur,
                                'transferred_amt': self.job_cost_sheet.contract_budget_tra,
                                'used_amt': self.job_cost_sheet.contract_budget_used,
                            })]
                else:
                    line.append((0, 0, {
                        'scurve_id': self.id,
                        'month': month_date,
                        'year': year_date,
                        'planned_cost': self.job_cost_sheet.amount_total,
                        'purchased_amt': self.job_cost_sheet.contract_budget_pur,
                        'transferred_amt': self.job_cost_sheet.contract_budget_tra,
                        'used_amt': self.job_cost_sheet.contract_budget_used,
                    }))
                self.scurve_line_ids = line
                start_date = start_date + relativedelta(months=+1)
    
    def get_planned_progress_table(self): 
        workorders = []
        start_date = datetime.strptime(str(self.start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.end_date), "%Y-%m-%d")
        acc_progress = 0.0
        if self.method == 'progress': 
            self.scurve_line_ids = [(5, 0, 0)]
        if self.work_orders_ids:
            workorders.append((0, 0, {'workorder': self.work_orders_ids.ids,}))
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                line = []
                end_date = start_date + relativedelta(months=+1, days=-1)
                month_date = start_date.strftime("%B")
                year_date = start_date.strftime("%Y")
                line_src = self.env['scurve.line'].search([('scurve_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                for wo in self.work_orders_ids:
                    if wo.planned_end_date:
                        wo_month = wo.planned_end_date.strftime("%B")
                        wo_year = wo.planned_end_date.strftime("%Y")
                            
                        if wo_month == month_date and wo_year == year_date:
                            cal = wo.work_weightage * wo.stage_weightage / 100

                            acc_progress += cal

                            wo = [(2, wo.id, 0)]

                if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                    end_date = ends_date

                if line_src:
                    self.scurve_line_ids = [(1, line_src.id, {
                                'planned_progress': acc_progress,
                            })]
                else:
                    line.append((0, 0, {
                        'scurve_id': self.id,
                        'month': month_date,
                        'year': year_date,
                        'planned_progress': acc_progress,
                    }))
                self.scurve_line_ids = line
                start_date = start_date + relativedelta(months=+1)    

    def get_actual_cost_table(self):
        amount = 0.0
        actual_amount_total = 0.0
        if self.project_budget:
            for line in self.scurve_line_ids:
                amount_material = 0.0
                amount_labour = 0.0
                amount_overhead = 0.0
                amount_subcon = 0.0
                amount_equipment = 0.0
                amount_asset = 0.0
                budget = self.env['project.budget'].search([('project_id', '=', self.project_id.id), ('month.month', '=', line.month), ('month.year', '=', line.year)])
                for line_b in budget.budget_material_ids:
                    amount_material += line_b.amt_used

                for line_b in budget.budget_labour_ids:
                    amount_labour += line_b.amt_used

                for line_b in budget.budget_subcon_ids:
                    amount_subcon += line_b.amt_used

                for line_b in budget.budget_overhead_ids:
                    amount_overhead += line_b.amt_used

                for line_b in budget.budget_equipment_ids:
                    amount_equipment += line_b.amt_used

                for line_b in budget.budget_internal_asset_ids:
                    amount_asset += line_b.actual_used_amt
                actual_amount_total += (amount_material + amount_labour + amount_subcon + amount_overhead + amount_equipment + amount_asset)
                line.actual_cost = actual_amount_total
        else:
            amount = self.job_cost_sheet.contract_budget_used
            for line in self.scurve_line_ids:
                line.actual_cost = amount

    def get_actual_progress_table(self):
        workorders = []
        acc_progress = 0.0
        start_date = datetime.strptime(str(self.start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.end_date), "%Y-%m-%d")
        if self.work_orders_ids:
            workorders.append((0, 0, {'workorder': self.work_orders_ids.ids,}))
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                end_date = start_date + relativedelta(months=+1, days=-1)
                month_date = start_date.strftime("%B")
                year_date = start_date.strftime("%Y")
                line_src = self.env['scurve.line'].search([('scurve_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                for wo_act in self.work_orders_ids:
                    if wo_act.actual_end_date:
                        wo_month = wo_act.actual_end_date.strftime("%B")
                        wo_year = wo_act.actual_end_date.strftime("%Y")
                        if wo_month == month_date and wo_year == year_date:
                            cal1 = wo_act.work_weightage * wo_act.stage_weightage / 100
                            # if wo_act.progress_history_ids:
                            #     for progress in wo_act.progress_history_ids:
                            #         ph_month = progress.progress_end_date.strftime("%B")
                            #         ph_year = progress.progress_end_date.strftime("%Y")
                            #         if ph_month == month_date and ph_year == year_date:
                            #             cal = progress.progress * cal1 / 100
                            #             acc_progress += cal
                            #             progress = [(2, progress.id, 0)]
                            acc_progress += cal1
                if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                    end_date = ends_date
                self.scurve_line_ids = [(1, line_src.id, {
                            'actual_progress': acc_progress,
                        })]
                start_date = start_date + relativedelta(months=+1)

    def get_plan_cost_from_table(self):
        planned = []
        cost = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                cost = line.planned_cost
                planned.append(cost)
            return planned
    
    def get_plan_progress_from_table(self):
        planned = []
        acc_progress = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                prog = line.planned_progress
                acc_progress = prog
                planned.append(acc_progress)
            return planned

    def get_actual_cost_from_table(self):
        actual = []
        acc_actual = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                prog = line.actual_cost
                acc_actual = prog
                actual.append(acc_actual)
            return actual

    def get_actual_progress_from_table(self):
        actual = []
        acc_progress = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                prog = line.actual_progress
                acc_progress = prog
                actual.append(acc_progress)
            return actual
    
    def get_plan_cost_progress_from_table(self):
        planned = []
        cost = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                prog = line.prog_planned_cost
                cost = prog
                planned.append(cost)
            return planned

    def get_all_cost_from_table(self, purchased, transferred, used):
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                pur = line.purchased_amt
                tra = line.transferred_amt
                use = line.used_amt
                purchased.append(pur)
                transferred.append(tra)
                used.append(use)
            return purchased, transferred, used
    
    def get_actual_cost_progress_from_table(self):
        actual = []
        acc_progress = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                prog = line.prog_actual_cost
                acc_progress = prog
                actual.append(acc_progress)
            return actual
    
    def create_scurve(self, final_dict):
        for record in self:
            final_dict = {}
            month = record.get_month()
            label_1 = ''
            label_2 = ''
            
            # planned = self.get_planned()
            # actual = self.get_actual()
            # self.get_labels()

            if record.method == 'cost':
                name = record.get_labels()
                record.get_planned_cost_table()
                record.get_actual_cost_table()
                planned = record.get_plan_cost_from_table()
                actual = record.get_actual_cost_from_table()
                label_1 = 'Planned '
                label_2 = 'Actual '
                name1 = name
                name2 = name
            
            elif record.method == 'progress': 
                name = record.get_labels()
                record.get_planned_progress_table()
                record.get_actual_progress_table()
                planned = record.get_plan_progress_from_table()
                actual = record.get_actual_progress_from_table()
                label_1 = 'Planned '
                label_2 = 'Actual '
                name1 = name
                name2 = name

            elif record.method == 'cvp': 
                record.get_planned_progress_table()
                record.get_planned_cost_table()
                record.get_actual_progress_table()
                record.get_actual_cost_table()
                record.scurve_line_ids._compute_plan_cost_progress()
                record.scurve_line_ids._compute_actual_cost_progress()
                actual = record.get_actual_cost_progress_from_table()
                planned = record.get_actual_progress_from_table()
                name1 = 'Progress(%)'
                name2 = 'Cost(%)'
                label_1 = 'Actual '
                label_2 = 'Actual '
            
            elif record.method == 'pa_costprog':
                record.get_planned_progress_table()
                record.get_planned_cost_table()

                record.get_actual_progress_table()
                record.get_actual_cost_table()

                record.scurve_line_ids._compute_plan_cost_progress()
                record.scurve_line_ids._compute_actual_cost_progress()
                planned = record.get_plan_cost_progress_from_table()
                planned1 = record.get_plan_progress_from_table()
                actual = record.get_actual_cost_progress_from_table()
                actual1 = record.get_actual_progress_from_table()
                name1 = 'Cost'
                name2 = 'Progress(%)'
                label_1 = 'Planned '
                label_2 = 'Actual '

            elif record.method == 'all':
                purchased = []
                transferred = []
                used = []
                name = record.get_labels()
                record.get_planned_cost_table()
                record.get_all_cost_from_table(purchased, transferred, used)
                label_1 = 'Purchased '
                label_2 = 'Transferred '
                label_3 = 'Used '
                name1 = name
                name2 = name
            
            if record.method == 'pa_costprog': 
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
                record.ks_chart_data = json.dumps(final_dict)
                return final_dict

            elif record.method == 'all': 
                final_dict.update({
                    'labels': month,
                    'datasets': [{
                        'data' : purchased,
                        'label': label_1 + name1,
                        }, {
                        'data' : transferred,
                        'label': label_2 + name1,
                        }, {
                        'data' : used,
                        'label': label_3 + name1,
                        }]
                    })
                record.ks_chart_data = json.dumps(final_dict)
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
                record.ks_chart_data = json.dumps(final_dict)
                return final_dict

    @api.depends('work_orders_ids', 'method')
    def _compute_work_order_count(self):
        for record in self:
            record.work_order_count = len(record.work_orders_ids)  
            data =  record.scurve_create_data_dict(record.project_id)
            record.create_scurve(data)
    
    def cons_scurve_print(self):
        pass


class ScurveLine(models.TransientModel):
    _name = 'scurve.line'
    _description = "Scurve Line"

    scurve_id = fields.Many2one(comodel_name='construction.scurve', string='Scurve Line')
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
    actual_cost = fields.Float(string='Actual Cost')
    purchased_amt = fields.Float(string='Purchased Amount')
    transferred_amt = fields.Float(string='Transferred Amount')
    used_amt = fields.Float(string='Used Amount')
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
            cost = 0
            if line.contract_amount > 0:
                cost = line.planned_cost / line.contract_amount * 100
            line.prog_planned_cost = cost

    def _compute_actual_cost_progress(self):
        for line in self:
            cost = 0
            if line.contract_amount > 0:
                cost = line.actual_cost / line.contract_amount * 100
            line.prog_actual_cost = cost

    @api.depends('scurve_id.scurve_line_ids', 'scurve_id.scurve_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.scurve_id.scurve_line_ids:
                no += 1
                l.sr_no = no