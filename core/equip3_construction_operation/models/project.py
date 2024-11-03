# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, _logger
import json


class ProjectProject(models.Model):
    _inherit = 'project.project'

    cost_sheet_count = fields.Integer(string='Cost Sheet', compute='_comute_cost_sheet')
    act_start_date = fields.Date(string='Actual Start Date')
    act_end_date = fields.Date(string='Actual End Date')
    working_hour = fields.Float(string='Working Hour', default="480")
    working_hour_hours = fields.Float(string='Working Hours (Hour)', default=8.0)
    cost_sheet = fields.Many2one(comodel_name='job.cost.sheet', string='Cost Sheet', compute='_get_cost_sheet')

    # Cost and Revenue
    estimation_material_cost = fields.Float(string='Estimation Material Cost', compute='_compute_cost')
    estimation_labour_cost = fields.Float(string='Estimation Labour Cost', compute='_compute_cost')
    estimation_overhead_cost = fields.Float(string='Estimation Overhead Cost', compute='_compute_cost')
    estimation_asset_cost = fields.Float(string='Estimation Internal Asset Cost', compute='_compute_cost')
    estimation_equipment_cost = fields.Float(string='Estimation Equipment Cost', compute='_compute_cost')
    estimation_subcon_cost = fields.Float(string='Estimation Subcon Cost', compute='_compute_cost')
    total_estimation_cost = fields.Float(string='Total Estimation Cost', compute='_compute_cost', store=True)
    total_estimation_revenue = fields.Float(string='Total Estimation Revenue', compute='_compute_cost', store=True)
    total_estimation_profit = fields.Float(string='Total Estimation Profit', compute='_compute_cost')
    # Actual
    actual_material_cost = fields.Monetary(string='Actual Material Cost', compute='_compute_cost')
    actual_labour_cost = fields.Float(string='Actual Labour Cost', compute='_compute_cost')
    actual_overhead_cost = fields.Float(string='Actual Overhead Cost', compute='_compute_cost')
    actual_asset_cost = fields.Float(string='Actual Internal Asset Cost', compute='_compute_cost')
    actual_equipment_cost = fields.Float(string='Actual Equipment Cost', compute='_compute_cost')
    actual_subcon_cost = fields.Float(string='Actual Subcon Cost', compute='_compute_cost')
    total_actual_cost = fields.Float(string='Total Actual Cost', compute='_compute_cost', store=True)

    total_actual_revenue = fields.Float(string='Total Actual Revenue', store=True)
    total_actual_profit = fields.Float(string='Total Actual Profit', compute='_compute_cost', store=True)
    purchased_amount = fields.Float(string='Purchased Amount', compute='_compute_cost', store=True)
    transferred_amount = fields.Float(string='Transferred Amount', compute='_compute_cost', store=True)
    used_amount = fields.Float(string='Used Amount', compute='_compute_cost', store=True)

    project_completion = fields.Float(string='Project Progress', readonly=True)
    project_issue_count = fields.Integer(string='Issue', readonly=True, compute='compute_issue_count', store=True)
    s_curve_stat = fields.Integer(string='S-Curve', readonly=True)
    budget_count = fields.Integer(string='Budget Count', compute='compute_budget_count', store=True)
    is_set_projects_type = fields.Boolean(string='Set Projects Type', default=False, store=True)
    progress = fields.Float(string='Project Progress (%)', compute='_compute_cost', store=True)

    budgeting_method = fields.Selection([
        ('product_budget', 'Based on Product Budget'),
        ('gop_budget', 'Based on Group of Product Budget'),
        ('budget_type', 'Based on Budget Type'),
        ('total_budget', 'Based on Total Budget')], string='Budgeting Method', default='product_budget', readonly='')
    budgeting_period = fields.Selection([
        ('project', 'Project Length Budgeting'),
        ('monthly', 'Monthly Budgeting'),
        ('custom', 'Custom Time Budgeting'), ], string='Budgeting Period', default='monthly')
    ks_chart_data = fields.Text(string=_("Chart Data"), default='')
    ks_graph_view = fields.Integer(string="Graph view", default=0)
    # hr_timesheet
    is_hide_allow_timesheets = fields.Boolean(string="dummy_allow_timesheets", compute='_compute_allow_timesheets', compute_sudo=True)

    # Custom project progress
    is_custom_project_progress = fields.Boolean(string='Custom Project Progress')
    custom_project_progress = fields.Selection([
        ('manual_estimation', 'Manual Estimation'),
    ], string='Progress (Job Order) Based On', default='manual_estimation')

    # ('budget_estimation', 'Budget Used'),

    asset_allocation_option = fields.Selection([
        ('manual_count', 'Input Duration'),
        ('live_count', 'Live Duration'),
    ], string='Duration (Asset) Based On', default='manual_count')

    budget_period_history_ids = fields.One2many('budget.period.history', 'project_id', string='Budget Period History')
    budget_period_id = fields.Many2one('project.budget.period', string='Period', compute='_compute_budget_period')

    @api.constrains('working_hour_hours')
    def _check_working_hour_hours(self):
        for record in self:
            if record.is_using_labour_attendance:
                if record.working_hour_hours <= 0:
                    raise ValidationError(_('Working hours can`t be less or equal to zero.'))

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.context.get('is_project_job_order'):
            domain.append(('id', 'in', self.env.user.project_ids.ids))
        if self.env.context.get('from_api'):
            if self.env.user.has_group(
                    'abs_construction_management.group_construction_user') and not self.env.user.has_group(
                    'equip3_construction_accessright_setting.group_construction_director'):
                domain.append(('id', 'in', self.env.user.project_ids.ids))
                domain.append(('primary_states', 'not in', ('draft', 'lost')))
            else:
                domain.append(('primary_states', 'not in', ('draft', 'lost')))

        return super(ProjectProject, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def search_count(self, domain):
        domain = domain or []
        if self.env.context.get('from_api'):
            if self.env.user.has_group(
                    'abs_construction_management.group_construction_user') and not self.env.user.has_group(
                    'equip3_construction_accessright_setting.group_construction_director'):
                domain.append(('id', 'in', self.env.user.project_ids.ids))
                domain.append(('primary_states', 'not in', ('draft', 'lost')))
            else:
                domain.append(('primary_states', 'not in', ('draft', 'lost')))

        return super(ProjectProject, self).search_count(domain)

    def custom_menu_management(self):
        views = [(self.env.ref('equip3_construction_masterdata.view_project_kanban_const').id, 'kanban'),
                 (self.env.ref('project.view_project').id, 'tree'),
                 (self.env.ref('project.edit_project').id, 'form'),
                 ]
        search_view_id = self.env.ref("project.view_project_project_filter").id
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_director'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Projects',
                'res_model': 'project.project',
                'view_mode': 'kanban,tree,form',
                'views': views,
                'domain': [('id', 'in', self.env.user.project_ids.ids), ('primary_states', 'not in', ('draft', 'lost')),
                           ('department_type', '=', 'project')],
                'context': {'default_department_type': 'project'},
                'search_view_id': search_view_id,
                'help': """
                 <p class="oe_view_nocontent_create">
                    Create a new project.
                </p><p>
                    Organize your activities (plan tasks, track issues, invoice timesheets) for internal, personal or customer projects.
                </p>
            """
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Projects',
                'res_model': 'project.project',
                'view_mode': 'kanban,tree,form',
                'views': views,
                'domain': [('department_type', '=', 'project'), ('primary_states', 'not in', ('draft', 'lost'))],
                'context': {'default_department_type': 'project'},
                'search_view_id': search_view_id,
                'help': """
                 <p class="oe_view_nocontent_create">
                    Create a new project.
                </p><p>
                    Organize your activities (plan tasks, track issues, invoice timesheets) for internal, personal or customer projects.
                </p>
            """
            }

    def _compute_allow_timesheets(self):
        for rec in self:
            equip3_construction_hr_operation = self.env['ir.module.module'].search(
                [('name', '=', 'equip3_construction_hr_operation')])
            if not equip3_construction_hr_operation or equip3_construction_hr_operation.state != 'installed':
                rec.is_hide_allow_timesheets = True
                rec.write({
                    'allow_timesheets': False,
                })
            else:
                rec.is_hide_allow_timesheets = False
                rec.write({
                    'allow_timesheets': False,
                })
    def _compute_budget_period(self):
        for rec in self:
            period = self.env['project.budget.period'].search([('project', '=', rec.id), ('state', '!=', 'closed')])
            rec.budget_period_id = period

    def compute_issue_count(self):
        for rec in self:
            issue_obj = rec.env['project.issue'].search_count([('project_id', '=', rec.id)])

    def compute_budget_count(self):
        for rec in self:
            budget_obj = rec.env['project.budget'].search_count([('project_id', '=', rec.id)])

    def action_project_issue(self):
        return {
            'name': ("Project Issue"),
            'view_mode': 'tree,form',
            'res_model': 'project.issue',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_id', '=', self.id)],
        }

    def action_request_change_period(self):
        return {
            'name': _('Request Change Period'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'request.change.period',
            'context': {
                'default_project_id': self.id,
                'default_current_start_date': self.start_date,
                'default_current_end_date': self.end_date,
                'default_planned_start_date': self.act_start_date if self.act_start_date else self.start_date,
                'default_is_date_readonly': self.act_start_date != False,
            },
        }

    def action_project_budget(self):
        return {
            'name': ("Project Budget"),
            'view_mode': 'tree,form',
            'res_model': 'project.budget',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_id', '=', self.id)],
        }

    def action_job_order_cons(self):
        return {
            'name': ("Job Orders"),
            'view_mode': 'tree,form',
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_id', '=', self.id)],
        }

    def action_s_curve(self):
        scurve_id = self.action_recompute_s_curve()
        return scurve_id.get_formview_action()

    def cron_recompute_s_curve(self):
        records = self.env['project.project'].search([])
        for res in records:
            if res.primary_states == 'draft': continue
            bud = res.env['project.budget'].search([('project_id', '=', res.id)])
            workorders = res.env['project.task'].search([('project_id', '=', res.id)])
            scurve_id = self.env['construction.scurve'].create({
                'name': res.name,
                'project_id': res.id,
                'start_date': res.start_date,
                'end_date': res.end_date,
                'job_cost_sheet': res.cost_sheet.id,
                'project_budget': bud,
                'contract_amount': res.total_estimation_cost,
                'work_orders_ids': [(6, 0, workorders.ids)],
                'method': 'cvp',
            })
            scurve_id.create_scurve({})
            chart_data = json.loads(scurve_id.ks_chart_data)
            if chart_data['labels']:
                if len(chart_data['labels']) > 6:
                    chart_data['labels'] = chart_data['labels'][-6:]
                    for dataset in chart_data['datasets']:
                        dataset['data'] = dataset['data'][-6:]

            res.ks_chart_data = json.dumps(chart_data)
            res.ks_graph_view = 1
        return True

    def action_recompute_s_curve(self):
        for res in self:
            bud = res.env['project.budget'].search([('project_id', '=', res.id)])
            workorders = res.env['project.task'].search([('project_id', '=', res.id)])
            scurve_id = self.env['construction.scurve'].create({
                'name': res.name,
                'project_id': res.id,
                'start_date': res.start_date,
                'end_date': res.end_date,
                'job_cost_sheet': res.cost_sheet.id,
                'project_budget': bud,
                'contract_amount': res.total_estimation_cost,
                'work_orders_ids': [(6, 0, workorders.ids)],
                'method': 'cvp',
            })
            scurve_id.create_scurve({})
            chart_data = json.loads(scurve_id.ks_chart_data)
            if chart_data['labels']:
                if len(chart_data['labels']) > 6:
                    chart_data['labels'] = chart_data['labels'][-6:]
                    for dataset in chart_data['datasets']:
                        dataset['data'] = dataset['data'][-6:]

            res.ks_chart_data = json.dumps(chart_data)
            res.ks_graph_view = 1
        return scurve_id

    def _get_cost_sheet(self):
        for res in self:
            cost = self.env['job.cost.sheet'].search([('project_id', '=', res.id), ('state', 'not in', ['cancelled', 'reject', 'revised'])], limit=1)
            self.write({'cost_sheet': cost})
    
    def _comute_cost_sheet(self):
        for project in self:
            job_cost_sheet_obj = self.env['job.cost.sheet'].search(
                [('project_id', '=', project.id), ('state', '!=', 'cancelled')])
            count = 0
            if job_cost_sheet_obj:
                for sheet in job_cost_sheet_obj:
                    if sheet:
                        count += 1
            project.cost_sheet_count = count

    def action_view_cost_sheet(self):
        return {
            'name': _('Cost Sheet'),
            'domain': [('project_id', '=', self.id), ('state', '!=', 'cancelled')],
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'job.cost.sheet',
            'view_id': False,
            'views': [(self.env.ref('abs_construction_management.view_job_cost_sheet_menu_tree').id, 'tree'),
                      (self.env.ref('abs_construction_management.view_job_cost_sheet_menu_form').id, 'form')],
            'type': 'ir.actions.act_window'
        }

    def _get_project_budget(self):
        bud = self.env['project.budget'].search([('project_id', '=', self.id)])
        return bud

    def _compute_actual_budget(self, material, labour, overhead, equipment, subcon, sub_total):
        budget = self.env['project.budget'].search([('project_id', '=', self.id)])
        for bud in budget:
            for mat in bud.budget_material_ids:
                material += mat.amt_used
            for lab in bud.budget_labour_ids:
                labour += lab.amt_used
            for ove in bud.budget_overhead_ids:
                overhead += ove.amt_used
            for equ in bud.budget_equipment_ids:
                equipment += equ.amt_used
            for sub in bud.budget_subcon_ids:
                subcon += sub.amt_used
            sub_total = material + labour + overhead + equipment + subcon
        return material, labour, overhead, equipment, subcon, sub_total

    def _compute_cost(self):
        for rec in self:
            material = 0
            labour = 0
            overhead = 0
            asset = 0
            equipment = 0
            subcon = 0

            estimation_material = 0
            estimation_labour = 0
            estimation_overhead = 0
            estimation_asset = 0
            estimation_equipment = 0
            estimation_subcon = 0

            contract_exp_revenue = 0
            contract_exp_profit = 0
            for cos in rec.cost_sheet:
                material += sum( cos.material_ids.mapped('actual_used_amt') )
                labour += sum( cos.material_labour_ids.mapped('actual_used_amt') )
                overhead += sum( cos.material_overhead_ids.mapped('actual_used_amt') )
                asset += sum( cos.internal_asset_ids.mapped('actual_used_amt') )
                equipment += sum( cos.material_equipment_ids.mapped('actual_used_amt') )
                subcon += sum( cos.material_subcon_ids.mapped('actual_used_amt') )

                estimation_material += cos.amount_material
                estimation_labour += cos.amount_labour
                estimation_overhead += cos.amount_overhead
                estimation_asset += cos.amount_internal_asset
                estimation_equipment += cos.amount_equipment
                estimation_subcon += cos.amount_subcon

                contract_exp_revenue += cos.contract_exp_revenue
                contract_exp_profit += cos.contract_exp_profit

            rec.actual_material_cost = material
            rec.actual_labour_cost = labour
            rec.actual_overhead_cost = overhead
            rec.actual_asset_cost = asset
            rec.actual_equipment_cost = equipment
            rec.actual_subcon_cost = subcon
            rec.total_actual_cost = sum([material, labour, overhead, asset, equipment, subcon])

            rec.estimation_material_cost = estimation_material
            rec.estimation_labour_cost = estimation_labour
            rec.estimation_overhead_cost = estimation_overhead
            rec.estimation_asset_cost = estimation_asset
            rec.estimation_equipment_cost = estimation_equipment
            rec.estimation_subcon_cost = estimation_subcon
            rec.total_estimation_cost = sum([estimation_material, estimation_labour, estimation_overhead, estimation_asset, estimation_equipment, estimation_subcon])

            rec.total_estimation_revenue = contract_exp_revenue
            rec.total_estimation_profit = contract_exp_profit

            rec.total_actual_profit = rec.total_estimation_revenue - rec.total_actual_cost
            rec.progress = rec.compute_all_project_progress()
            rec.purchased_amount = rec.cost_sheet.contract_budget_pur
            rec.transferred_amount = rec.cost_sheet.contract_budget_tra
            rec.used_amount = rec.cost_sheet.contract_budget_used

    def button_suspend(self):
        rec = super(ProjectProject, self).button_suspend()
        for res in self:
            task_ids = self.env['project.task'].search([('project_id', '=', res.id)])
            for task in task_ids:
                task.state_before_pend = task.state
                task.write({'state': 'pending'})
        return rec

    def button_continue(self):
        rec = super(ProjectProject, self).button_continue()
        for res in self:
            task_ids = self.env['project.task'].search([('project_id', '=', res.id)])
            for task in task_ids:
                task.write({'state': task.state_before_pend})
        return res


class ProjectCompletionInherit(models.Model):
    _inherit = "project.completion.const"

    project_completion = fields.Float(string="Contract Completion", compute="compute_contract_completion")

    @api.depends('stage_details_ids')
    def compute_contract_completion(self):
        total = 0
        for rec in self:
            total = sum(rec.stage_details_ids.mapped('stage_completion'))
            rec.project_completion = total
        return total


class ProjectNewInherit(models.Model):
    _inherit = 'project.stage.const'

    stage_completion = fields.Float(string="Stage Completion (%)", compute="compute_stage_completion")

    def compute_stage_completion(self):
        for rec in self:
            work = self.env['project.task'].search(
                [('sale_order', '=', rec.sale_order.id), ('stage_new', '=', rec.id),
                 ('project_id.name', '=', rec.project_id),
                 ('state', '!=', 'draft')])
            total = sum(work.mapped('contract_completion'))
            rec.stage_completion = total


class BudgetPeriodHistory(models.Model):
    _name = 'budget.period.history'
    _description = 'Budget Period History'

    no = fields.Integer(string='No', compute='_sequence_ref')
    project_id = fields.Many2one('project.project', string='Project')
    previous_start_date = fields.Date(string='Previous Start Date')
    previous_end_date = fields.Date(string='Previous End Date')
    previous_duration = fields.Integer(string='Previous Duration')
    planned_start_date = fields.Date(string='Planned Start Date')
    planned_end_date = fields.Date(string='Planned End Date')
    planned_duration = fields.Integer(string='Planned Duration')
    reason = fields.Text(string='Reason')

    @api.depends('project_id')
    def _sequence_ref(self):
        for line in self:
            no = 0
            for l in line.project_id.budget_period_history_ids:
                no += 1
                l.no = no

