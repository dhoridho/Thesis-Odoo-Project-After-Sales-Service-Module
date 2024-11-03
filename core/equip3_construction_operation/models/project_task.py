import base64
import json

from odoo.tools import human_size
from email.policy import default
from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from pytz import timezone
from lxml import etree


class ProjectTaskNew(models.Model):
    _inherit = 'project.task'
    _description = "Work Order"

    @api.model
    def _domain_assigned_to(self):
        return [('company_id', '=', self.env.company.id)]

    @api.model
    def _domain_project(self):
        return [('company_id', '=', self.env.company.id), ('branch_id', 'in', self.env.branches.ids)]

    project_id = fields.Many2one('project.project', domain=_domain_assigned_to)
    stage = fields.Many2one('project.stage', string="Stage")
    stage_computed = fields.Many2many('project.stage', string='Stages', compute='get_stages')
    stage_weightage = fields.Float(string="Stage Weightage")
    actual_start_date = fields.Datetime(string="Actual Start Date")
    actual_end_date = fields.Datetime(string="Actual End Date")
    planned_start_date = fields.Datetime(string="Planned Start Date")
    planned_end_date = fields.Datetime(string="Planned End Date")
    parent_actual_start_date = fields.Datetime(string="Actual Start Date", related='parent_task.actual_start_date')
    parent_actual_end_date = fields.Datetime(string="Actual End Date", related='parent_task.actual_end_date')
    parent_planned_start_date = fields.Datetime(string="Planned Start Date", related='parent_task.planned_start_date')
    parent_planned_end_date = fields.Datetime(string="Planned End Date", related='parent_task.planned_end_date')
    project_director = fields.Many2one(related='project_id.project_director', string="Project Director")
    sub_contractor = fields.Many2one('res.partner', string="Sub Contractor")
    work_weightage = fields.Float(string="Work Order Weightage")
    work_weightage_remaining = fields.Float(string="Work Order Weightage Remaining", store=True)
    worker_assigned_to = fields.Many2one('hr.employee', string="PIC", domain=_domain_assigned_to)
    assigned_to = fields.Many2one('res.users', string="PIC", domain=_domain_assigned_to)
    employee_worker_ids = fields.Many2many('hr.employee', string="Workers", readonly=True, domain=_domain_assigned_to)
    worker_ids = fields.Many2many('res.users', 'user_worker_id', 'user_id', 'worker_id', string="Workers",
                                  domain=_domain_assigned_to)
    task_product_ids = fields.One2many('task.product.cons', 'task_product_id')
    project_scope_domain_dump = fields.Char(string="Project Scope Domain Dump", readonly=True,
                                            compute="_compute_project_scope_domain_dump")
    project_section_domain_dump = fields.Char(string="Project Scope Domain Dump", readonly=True,
                                            compute="_compute_project_section_domain_dump")
    labour_project_budget_ids = fields.Many2many('project.budget', string="Labour Budget")
    labour_project_scope_ids = fields.Many2many('project.scope.line', string="Project Scope", )
    labour_section_ids = fields.Many2many('section.line', string="Section")
    labour_usage_ids = fields.One2many('task.labour.usage', inverse_name='project_task_id', string="Labour Usage")
    consumed_material_ids = fields.One2many('consumed.material', 'consumed_id')
    consumed_equipment_ids = fields.One2many('consumed.equipment', 'consumed_id')
    consumed_labour_ids = fields.One2many('consumed.labour', 'consumed_id')
    consumed_overhead_ids = fields.One2many('consumed.overhead', 'consumed_id')
    consumed_history_ids = fields.One2many('consumed.history', 'consumed_id')
    consumed_material_history_ids = fields.One2many(comodel_name='consumed.material.history',
                                                    inverse_name='consumed_id', string='Consumed History')
    consumed_equipment_history_ids = fields.One2many(comodel_name='consumed.equipment.history',
                                                     inverse_name='consumed_id', string='Consumed History')
    consumed_labour_history_ids = fields.One2many(comodel_name='consumed.labour.history', inverse_name='consumed_id',
                                                  string='Consumed History')
    consumed_overhead_history_ids = fields.One2many(comodel_name='consumed.overhead.history',
                                                    inverse_name='consumed_id', string='Consumed History')
    subtask_ids = fields.One2many('project.subtask', 'subtask_id')
    progress_history_ids = fields.One2many('progress.history', 'work_order', string='Progress History')
    project_progress = fields.Float(string="Project Progress")
    number = fields.Char(string='Work Order ID', required=True, copy=False, readonly=True,
                         states={'draft': [('readonly', True)]}, index=True, default=lambda self: _('New'))
    is_subtask = fields.Boolean(string="Is a Subtask", default=False)
    parent_task = fields.Many2one('project.task', string="Parent Task")
    is_subcon = fields.Boolean(string='Is Subcon', default=False)
    cost_sheet = fields.Many2one(comodel_name='job.cost.sheet', string='Cost Sheet', required=True)
    project_budget = fields.Many2one(comodel_name='project.budget', string='Project Budget', readonly=True)
    gantt_chart_color = fields.Char(string="Gantt Chart Color", required=True,
                                    help="Please set Hex color for Gantt Chart.", default="#7B7BAD")
    claim_request = fields.Boolean(string="Claim Request")
    last_progress = fields.Float(string="Last WO Progress")
    total_product_usage = fields.Integer(compute='_compute_product_usage', string='Material Usage')
    total_asset_allocation = fields.Integer(compute='_compute_asset_allocation', string='Asset Allocation')
    progress_task = fields.Float(string="Progress", compute="compute_progress_task", group_operator='avg', store=True)
    stage_completion = fields.Float(string="Stage Completion", compute="compute_contract_completion")
    contract_completion = fields.Float(string="Contract Completion", compute="compute_contract_completion")
    assigned_date = fields.Datetime(string="Assigned Date")
    date_deadline = fields.Datetime(string='Deadline', index=True, copy=False, tracking=True)
    new_description = fields.Html(string='Description')
    stage_new = fields.Many2one('project.stage.const', string="Stage")
    stage_computed_new = fields.Many2many('project.stage.const', string='Stages', compute='get_stages_new')
    completion_ref = fields.Many2one('project.completion.const', string="Contract")
    sale_order = fields.Many2one('sale.order.const', string="Contract")
    job_estimate = fields.Many2one('job.estimate', string="BOQ")
    purchase_subcon = fields.Many2one('purchase.order', string="Contract")
    rest_weightage = fields.Float(string="Remaining Weightage")
    rest_weightage_string = fields.Char(string="Remaining Weightage")
    work_subcon_weightage = fields.Float(string="Job Subcon Weightage")
    work_subcon_remaining = fields.Float(string="Job Subcon Weightage Remaining")
    contract_completion_subcon = fields.Float(string="Contract Completion Subcon",
                                              compute="compute_contract_completion_subcon")
    work_subtask_weightage = fields.Float(string="Subtask Weightage")
    subtask_count = fields.Integer("Sub-task count", compute='_compute_count_subtask')
    subtask_exist = fields.Boolean(string="Subtask Exist", compute='_compute_subtask_count_bool')
    sub_task_desc = fields.Text(string="Description")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('inprogress', 'Progress'),
        ('pending', 'Pending'),
        ('complete', 'Complete'),
        ('cancel', 'Canceled'),
    ], string='State', default='draft')
    state_before_pend = fields.Selection([
        ('draft', 'Draft'),
        ('inprogress', 'Progress'),
        ('pending', 'Pending'),
        ('complete', 'Complete'),
        ('cancel', 'Canceled'),
    ])

    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, readonly=True,
                                 default=lambda self: self.env.company)
    branch_id = fields.Many2one(related='project_id.branch_id', string="Branch",
                                default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids),
                                                     ('company_id', '=', self.env.company.id)])
    creation_date = fields.Date("Creation Date", readonly=True, default=fields.Date.today())
    create_by = fields.Many2one('res.users', 'Created by', readonly=True, default=lambda self: self.env.user)
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')

    related_subtask_ids = fields.Many2many("project.task",
                                           relation="task_rel_id",
                                           column1="task_id",
                                           column2="subtask_id",
                                           string="")
    reason_status = fields.Text('Reason of Status')
    budgeting_period = fields.Selection(related='project_id.budgeting_period', string='Budgeting Period')
    custom_project_progress = fields.Selection(related='project_id.custom_project_progress',
                                               string='Custom Project Progress')
    active_location_ids = fields.Many2many('project.location', string='Active Locations')
    is_using_labour_attendance = fields.Boolean(related='project_id.is_using_labour_attendance',)
    project_location_domain_dump = fields.Char(string="Project Location Domain Dump",
                                               compute="_compute_project_location_domain_dump")

    @api.depends('project_id', 'active_location_ids')
    def _compute_project_location_domain_dump(self):
        for rec in self:
            project_location_ids = rec.project_id.project_location_ids.ids
            if project_location_ids:
                rec.project_location_domain_dump = json.dumps([('id', 'in', project_location_ids)])
            else:
                rec.project_location_domain_dump = json.dumps([('id', 'in', False)])

    @api.model
    def search_count(self, domain):
        domain = domain or []
        if self.env.context.get("from_api"):
            if self.env.user.has_group(
                    'abs_construction_management.group_construction_user') and not self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_engineer'):
                domain.append(('worker_ids.id', 'in', [self.env.user.id]))
            elif self.env.user.has_group(
                    'equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group(
                'abs_construction_management.group_construction_manager'):
                domain.append(('worker_ids.id', 'in', [self.env.user.id]))
            elif self.env.user.has_group(
                    'abs_construction_management.group_construction_manager') and not self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_director'):
                domain.append(('project_id', 'in', self.env.user.project_ids.ids))

        return super(ProjectTaskNew, self).search_count(domain)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_engineer'):
            domain.append(('worker_ids.id', 'in', [self.env.user.id]))
        elif self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group(
            'abs_construction_management.group_construction_manager'):
            domain.append(('worker_ids.id', 'in', [self.env.user.id]))
        elif self.env.user.has_group(
                'abs_construction_management.group_construction_manager') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))

        return super(ProjectTaskNew, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ProjectTaskNew, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        root = etree.fromstring(res['arch'])
        context = self._context
        if not 'ks_gantt' in res['arch']:
            if self.env.user.has_group(
                    'abs_construction_management.group_construction_user') and not self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_engineer'):
                root.set('create', 'false')
                root.set('edit', 'false')
                root.set('delete', 'false')
                res['arch'] = etree.tostring(root)
            elif self.env.user.has_group(
                    'equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group(
                'abs_construction_management.group_construction_manager'):
                if view_type == 'tree' or 'form':
                    if 'default_is_subcon' in context:
                        if context['default_is_subcon']:
                            root.set('create', 'false')
                        else:
                            root.set('create', 'true')
                    else:
                        root.set('create', 'true')
                else:
                    root.set('create', 'true')
                root.set('edit', 'true')
                root.set('delete', 'false')
                res['arch'] = etree.tostring(root)
            else:
                if view_type == 'tree' or 'form':
                    if 'default_is_subcon' in context:
                        if context['default_is_subcon']:
                            root.set('create', 'false')
                        else:
                            root.set('create', 'true')
                    else:
                        root.set('create', 'true')
                else:
                    root.set('create', 'true')
                root.set('edit', 'true')
                root.set('delete', 'true')
                res['arch'] = etree.tostring(root)

        return res

    # depth = 0 -> get all subtask
    # depth = 1 -> get only direct subtask
    def _get_subtask(self, depth=1):
        for rec in self:
            all_subtask = rec.related_subtask_ids
            if depth == 1:
                return all_subtask
            else:
                subtask = all_subtask
                while subtask:
                    for sub in subtask:
                        if sub.related_subtask_ids:
                            all_subtask += sub.related_subtask_ids
                            subtask = sub.related_subtask_ids
                        else:
                            subtask = False
            return all_subtask

    def _compute_count_subtask(self):
        for res in self:
            subtask = len(res._get_subtask(depth=1))
            res.subtask_count = subtask

    @api.depends('project_id', 'labour_project_budget_ids')
    def _compute_project_scope_domain_dump(self):
        for rec in self:
            project_scope = self.project_id.project_scope_ids.mapped('project_scope')
            if rec.budgeting_period != 'project':
                labour_scopes = False
                for budget in rec.labour_project_budget_ids:
                    if not labour_scopes:
                        labour_scopes = budget.budget_labour_ids.mapped('project_scope').ids
                    else:
                        labour_scopes += budget.budget_labour_ids.mapped('project_scope').ids
                rec.project_scope_domain_dump = json.dumps(
                    [('id', 'in', project_scope.ids), ('id', 'in', labour_scopes)])
            else:
                rec.project_scope_domain_dump = json.dumps([('id', 'in', project_scope.ids)])

    @api.depends('labour_project_scope_ids', 'labour_section_ids')
    def _compute_project_section_domain_dump(self):
        for rec in self:
            section_ids = []
            if rec.project_id.project_section_ids:
                if rec.budgeting_period != 'project':
                    for line in rec.project_id.project_section_ids:
                        if (line.section and line.project_scope.id in rec.labour_project_scope_ids.ids
                                and (line.section.id in rec.labour_project_budget_ids.budget_labour_ids.section_name.ids
                                )):
                            section_ids.append(line.section.id)
                else:
                    for line in rec.project_id.project_section_ids:
                        if (line.section and line.project_scope.id in rec.labour_project_scope_ids.ids):
                            section_ids.append(line.section.id)

                # Remove section if corresponding scope is removed
                for section in rec.labour_section_ids:
                    project_sections = rec.project_id.project_section_ids.filtered(
                        lambda x: x.section.id == section._origin.id)
                    is_exist = False
                    for item in project_sections:
                        if item.project_scope.id in rec.labour_project_scope_ids.ids:
                            is_exist = True
                    if not is_exist:
                        rec.labour_section_ids = [(3, section.id)]
            rec.project_section_domain_dump = json.dumps([('id', 'in', section_ids)])

    @api.onchange('department_type', 'project_id')
    def _onchange_department_type(self):
        for rec in self:
            if self.env.user.has_group(
                    'abs_construction_management.group_construction_user') and not self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_director'):
                if rec.department_type == 'project':
                    return {
                        'domain': {
                            'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id),
                                           ('branch_id', '=', self.env.branches.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {
                            'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id),
                                           ('branch_id', '=', self.env.branches.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {
                            'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id),
                                           ('branch_id', '=', self.env.branches.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {
                            'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id),
                                           ('branch_id', '=', self.env.branches.ids)]}
                    }

    #Approval Matrix
    is_progress_history_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                         compute='_compute_is_customer_approval_matrix')

    @api.depends('project_id')
    def _compute_is_customer_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_progress_history_approval_matrix = IrConfigParam.get_param('is_progress_history_approval_matrix')
        for record in self:
            record.is_progress_history_approval_matrix = is_progress_history_approval_matrix

    # @api.onchange('stage_new','work_weightage')
    # def _compute_work_weightage_remaining(self):
    #     for line in self:
    #         total = 0.0
    #         for rec in self.env['project.task'].search([('is_subcon','=',False),('is_subtask','=',False),('project_id', '=', line.project_id.id), ('sale_order', '=', line.sale_order.id), ('stage_new', '=', line.stage_new.id)]):
    #             total += rec.work_weightage
    #         line.work_weightage_remaining = 100.0 - total

    # @api.depends('purchase_subcon','work_subcon_weightage')
    # def _compute_subcon_weightage_remaining(self):
    #     for line in self:
    #         total = 0.0
    #         for rec in self.env['project.task'].search([('is_subcon','=',True),('is_subtask','=',False),('project_id', '=', line.project_id.id), ('sale_order', '=', line.sale_order.id), ('purchase_subcon', '=', line.purchase_subcon.id)]):
    #             total += rec.work_subcon_remaining
    #         line.work_subcon_remaining = 100.0 - total

    @api.onchange('stage_new', 'work_weightage', 'work_subtask_weightage')
    def onchange_rest_weightage(self):
        for res in self:
            total_weig = 0
            rest_weig = 0
            total_weig_sub = 0
            rest_weig_sub = 0
            progress_parent = 0

            if res.stage_new:
                if res.is_subtask == False:
                    domain = [('is_subtask', '=', False), ('project_id', '=', res.project_id.id),
                         ('sale_order', '=', res.sale_order.id), ('stage_new', '=', res.stage_new.id)]
                    if res._origin.id:
                        domain += [('id', '!=', res._origin.id)]

                    other_task = self.env['project.task'].search(domain)
                    if other_task:
                        for rec in other_task:
                            total_weig += rec.work_weightage
                            rest_weig = 100 - total_weig
                    else:
                        rest_weig += 100

                    if rest_weig == 0:
                        raise ValidationError(
                            _('Remaining weightage for this stage is 0%. Cannot add job order for this stage anymore.'))
                    if res.work_weightage > rest_weig:
                        raise ValidationError(
                            _("The inputted job weightage exceeds remaining weightage for this stage. Please, re-set the weightage of this job order. (Remaining weightage = '{}%')".format(
                                rest_weig)))
                    elif res.work_weightage < 0:
                        raise ValidationError(
                            _('Job weightage cannot be less than 0%. Please, re-set the weightage of this job order.'))

                else:
                    progress_parent = res.parent_task.progress_task
                    domain = [('is_subtask', '=', True), ('project_id', '=', res.project_id.id),
                         ('parent_task', '=', res.parent_task.id)]
                    if res._origin.id:
                        domain += [('id', '!=', res._origin.id)]
                    subtask = self.env['project.task'].search(domain)
                    if subtask:
                        for sub in subtask:
                            total_weig_sub += sub.work_subtask_weightage
                            rest_weig_sub = 100 - progress_parent - total_weig_sub
                    else:
                        rest_weig_sub += 100 - progress_parent

                    if rest_weig_sub == 0:
                        raise ValidationError(
                            _('Remaining weightage for this parent task is 0%. Cannot add subtask for this parent task anymore.'))
                    if res.work_subtask_weightage > rest_weig_sub:
                        raise ValidationError(
                            _("The inputted job subtask weightage exceeds remaining weightage for this parent task. Please, re-set the weightage of this subtask. (Remaining weightage = '{}%')".format(
                                rest_weig_sub)))
                    elif res.work_subtask_weightage < 0:
                        raise ValidationError(
                            _('Job weightage cannot be less than 0%. Please, re-set the weightage of this job order.'))

    @api.onchange('purchase_subcon', 'work_subcon_weightage')
    def onchange_rest_weightage_subcon(self):
        for rec in self:
            total_weig = 0
            rest_weig = 0
            if rec.is_subcon == True:
                if rec.purchase_subcon:
                    if rec.is_subtask == False:
                        domain = [('is_subcon', '=', True), ('is_subtask', '=', False),
                             ('project_id', '=', rec.project_id.id), ('sale_order', '=', rec.sale_order.id),
                             ('purchase_subcon', '=', rec.purchase_subcon.id)]
                        if res._origin.id:
                            domain += [('id', '!=', res._origin.id)]
                        other_task = self.env['project.task'].search(domain)
                        if other_task:
                            for rec in other_task:
                                total_weig += rec.work_subcon_weightage
                                rest_weig = 100 - total_weig
                        else:
                            rest_weig += 100

                        if rest_weig == 0:
                            raise ValidationError(
                                _('Remaining weightage for this contract subcon is 0%. Cannot add job order subcon for this contract anymore.'))
                        if rec.work_subcon_weightage < 0:
                            raise ValidationError(
                                _('Job subcon weightage cannot be less than 0%. Please, re-set the weightage of this job order subcon.'))
                        elif rec.work_subcon_weightage > rest_weig:
                            raise ValidationError(
                                _("The inputted job subcon weightage exceeds remaining weightage for this contract subcon. Please, re-set the job subcon weightage of this job order. (Remaining weightage = '{}%')".format(
                                    rest_weig)))

    @api.onchange('date_deadline')
    def _onchange_date_deadline(self):
        if self.planned_end_date > self.date_deadline:
            raise ValidationError(_("Deadline should not be before the planned end date. Please re-set the deadline."))

    # @api.depends('subtask_ids')
    # def _compute_subtask_count(self):
    #     for task in self:
    #         task.subtask_count = len(task.subtask_ids)

    @api.depends('subtask_count')
    def _compute_subtask_count_bool(self):
        for task in self:
            if task.subtask_count > 0:
                task.subtask_exist = True
            else:
                task.subtask_exist = False

    # @api.onchange('labour_usage_ids')
    # def _onchange_labour_usage(self):
    #     for rec in self:
    #         workers_list = []
    #         for labour in rec.labour_usage_ids:
    #             for worker in labour.workers_ids:
    #                 if worker._origin.id not in rec.employee_worker_ids.ids:
    #                     workers_list.append(worker._origin)
    #         rec.employee_worker_ids += workers_list

    def get_labour_lines(self, project_scope, section=False, ):
        for rec in self:
            if section:
                labour_line = rec.env['material.labour'].search([
                    ('job_sheet_id', '=', rec.cost_sheet.id),
                    ('project_scope', '=', project_scope.id),
                    ('section_name', '=', section.id),
                ])
            else:
                labour_line = rec.env['material.labour'].search([
                    ('job_sheet_id', '=', rec.cost_sheet.id),
                    ('project_scope', '=', project_scope.id),
                ])
            return labour_line

    def _get_subtask_parents(self):
        for rec in self:
            if rec.is_subtask:
                parent = rec.parent_task
                subtask_parents = []

                while parent:
                    if parent == rec:
                        subtask = rec
                        if subtask.parent_task == rec:
                            subtask_exist = subtask.subtask_exist
                            if not subtask_exist:
                                return
                        break
                    subtask_parents.append(parent)
                    parent = parent.parent_task

                return subtask_parents[-1]

    def create_labour_usage(self):
        for rec in self:
            labour_usage = [(5, 0, 0)]
            if rec.labour_project_scope_ids:
                if rec.labour_section_ids:
                    for scope in rec.labour_project_scope_ids:
                        for section in rec.labour_section_ids:
                            labour_line = rec.get_labour_lines(scope, section)
                            for labour in labour_line:
                                budget_lines = self.env['budget.labour'].search([('cs_labour_id', '=', labour.id), (
                                    'budget_id', 'in', rec.labour_project_budget_ids.ids), ])
                                if budget_lines:
                                    for line in budget_lines:
                                        vals = {
                                            'project_task_id': rec.id,
                                            'cs_labour_id': labour.id,
                                            'bd_labour_id': line.id,
                                            'project_scope_id': scope.id,
                                            'section_id': section.id,
                                            'group_of_product_id': labour.group_of_product.id,
                                            'product_id': labour.product_id.id,
                                            'contractors': line.contractors,
                                            'time': line.time_left,
                                            'time_left': line.time_left,
                                            'uom_id': labour.uom_id.id,
                                            'unit_price': labour.price_unit,
                                            # 'workers_ids': [(6, 0, labour.workers_ids.ids)],
                                            'analytic_group_ids': [(6, 0, rec.cost_sheet.account_tag_ids.ids)],
                                        }
                                        if line.time_left > 0:
                                            labour_usage.append((0, 0, vals))
                                else:
                                    if rec.cost_sheet.budgeting_period == 'project':
                                        vals = {
                                            'project_task_id': rec.id,
                                            'cs_labour_id': labour.id,
                                            'bd_labour_id': False,
                                            'project_scope_id': scope.id,
                                            'section_id': section.id,
                                            'group_of_product_id': labour.group_of_product.id,
                                            'product_id': labour.product_id.id,
                                            'contractors': labour.contractors,
                                            'time': labour.time_left,
                                            'time_left': labour.time_left,
                                            'uom_id': labour.uom_id.id,
                                            'unit_price': labour.price_unit,
                                            # 'workers_ids': [(6, 0, labour.workers_ids.ids)],
                                            'analytic_group_ids': [(6, 0, rec.cost_sheet.account_tag_ids.ids)],
                                        }
                                        if labour.time_left > 0:
                                            labour_usage.append((0, 0, vals))
                elif not rec.labour_section_ids and rec.labour_project_scope_ids:
                    for scope in rec.labour_project_scope_ids:
                        labour_line = rec.get_labour_lines(scope)
                        for labour in labour_line:
                            budget_lines = self.env['budget.labour'].search([('cs_labour_id', '=', labour.id), (
                                'budget_id', 'in', rec.labour_project_budget_ids.ids), ])
                            if budget_lines:
                                for line in budget_lines:
                                    vals = {
                                        'project_task_id': rec.id,
                                        'cs_labour_id': labour.id,
                                        'bd_labour_id': line.id,
                                        'project_scope_id': scope.id,
                                        'section_id': labour.section_name.id,
                                        'group_of_product_id': labour.group_of_product.id,
                                        'product_id': labour.product_id.id,
                                        'contractors': line.contractors,
                                        'time': line.time_left,
                                        'time_left': line.time_left,
                                        'uom_id': labour.uom_id.id,
                                        'unit_price': labour.price_unit,
                                        # 'workers_ids': [(6, 0, labour.workers_ids.ids)],
                                        'analytic_group_ids': [(6, 0, rec.cost_sheet.account_tag_ids.ids)],
                                    }
                                    if line.time_left > 0:
                                        labour_usage.append((0, 0, vals))
                            else:
                                if rec.cost_sheet.budgeting_period == 'project':
                                    vals = {
                                        'project_task_id': rec.id,
                                        'cs_labour_id': labour.id,
                                        'bd_labour_id': False,
                                        'project_scope_id': scope.id,
                                        'section_id': labour.section_name.id,
                                        'group_of_product_id': labour.group_of_product.id,
                                        'product_id': labour.product_id.id,
                                        'contractors': labour.contractors,
                                        'time': labour.time_left,
                                        'time_left': labour.time_left,
                                        'uom_id': labour.uom_id.id,
                                        'unit_price': labour.price_unit,
                                        # 'workers_ids': [(6, 0, labour.workers_ids.ids)],
                                        'analytic_group_ids': [(6, 0, rec.cost_sheet.account_tag_ids.ids)],
                                    }
                                    if labour.time_left > 0:
                                        labour_usage.append((0, 0, vals))
            elif not rec.labour_section_ids and not rec.labour_project_scope_ids and rec.labour_project_budget_ids:
                for budget in rec.labour_project_budget_ids:
                    for labour in budget.budget_labour_ids:
                        vals = {
                            'project_task_id': rec.id,
                            'cs_labour_id': labour.cs_labour_id.id,
                            'bd_labour_id': labour.id,
                            'project_scope_id': labour.project_scope.id,
                            'section_id': labour.section_name.id,
                            'group_of_product_id': labour.group_of_product.id,
                            'product_id': labour.product_id.id,
                            'contractors': labour.contractors,
                            'time': labour.time_left,
                            'time_left': labour.time_left,
                            'uom_id': labour.uom_id.id,
                            'unit_price': labour.amount,
                            # 'workers_ids': [(6, 0, labour.workers_ids.ids)],
                            'analytic_group_ids': [(6, 0, rec.cost_sheet.account_tag_ids.ids)],
                        }
                        if labour.time_left > 0:
                            labour_usage.append((0, 0, vals))
            rec.labour_usage_ids = labour_usage

    def create_labour_usage_parent(self):
        for rec in self:
            labour_usage = [(5, 0, 0)]
            parent_task = rec._get_subtask_parents()
            for labour in parent_task.labour_usage_ids:
                vals = {
                    'project_task_id': rec.id,
                    'cs_labour_id': labour.cs_labour_id.id,
                    'bd_labour_id': labour.bd_labour_id.id or False,
                    'project_scope_id': labour.project_scope_id.id,
                    'section_id': labour.section_id.id,
                    'group_of_product_id': labour.group_of_product_id.id,
                    'product_id': labour.product_id.id,
                    'contractors': labour.contractors,
                    'time': labour.time,
                    'time_left': labour.time,
                    'uom_id': labour.uom_id.id,
                    'unit_price': labour.unit_price,
                    # 'workers_ids': [(6, 0, labour.workers_ids.ids)],
                    'analytic_group_ids': [(6, 0, rec.cost_sheet.account_tag_ids.ids)],
                }
                labour_usage.append((0, 0, vals))
            rec.labour_usage_ids = labour_usage

    def action_subtask(self):
        action = self.env["ir.actions.actions"]._for_xml_id("project.project_task_action_sub_task")

        # display all subtasks of current task
        action['domain'] = [('parent_task', '=', self.id), ('id', '!=', self.id)]

        # update context, with all default values as 'quick_create' does not contains all field in its view
        if self._context.get('default_project_id'):
            default_project = self.env['project.project'].browse(self.env.context['default_project_id'])
        else:
            default_project = self.project_id.subtask_project_id or self.project_id
        ctx = dict(self.env.context)
        ctx = {k: v for k, v in ctx.items() if not k.startswith('search_default_')}
        ctx.update({
            'default_name': self.env.context.get('name', self.name) + ':',
            'default_parent_id': self.id,  # will give default subtask field in `default_get`
            'default_company_id': default_project.company_id.id if default_project else self.env.company.id,
        })

        action['context'] = ctx

        return action

    def action_inprogress(self, is_labour_validated=False):
        for res in self:
            if not res.sale_order and res.is_subcon and res.department_type != 'department':
                raise ValidationError(_("Please set contract for this job order"))
            if not res.job_estimate and res.is_subcon and res.department_type != 'project':
                raise ValidationError(_("Please set BOQ for this job order"))
            if not res.stage_new and res.is_subcon:
                raise ValidationError(_("Please set stage for this job order"))
            if not res.planned_start_date and res.is_subcon:
                raise ValidationError(_("Please set planned start date for this job order"))
            if not res.planned_end_date and res.is_subcon:
                raise ValidationError(_("Please set planned end date for this job order"))

            if not is_labour_validated:
                if len(res.labour_usage_ids) > 0:
                    for labour in res.labour_usage_ids:
                        if not res.is_subtask:
                            if labour.time > labour.cs_labour_id.time_left:
                                raise ValidationError(
                                    _("The inputted time exceeds the remaining time for labour '{name}'."
                                      "Please, re-set the time of this labour. "
                                      "(Remaining time = '{time_left}')".
                                      format(name=labour.cs_labour_id.product_id.name,
                                             time_left=labour.cs_labour_id.time_left)))
                else:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Confirmation',
                        'view_mode': 'form',
                        'target': 'new',
                        'res_model': 'labour.usage.confirmation.wizard',
                        'context': {'default_project_task_id': self.id}
                    }

            if res.project_id.primary_states == 'suspended':
                raise ValidationError(_("Please continue the project first to continue this task"))
            else:
                if self.is_subtask == False and self.work_weightage == 0:
                    raise ValidationError(_("You haven't set job order weightage"))
                elif self.is_subtask == False and self.is_subcon == True and self.work_subcon_weightage == 0:
                    raise ValidationError(_("You haven't set job subcon weightage for this subcon"))
                elif self.is_subtask == False and self.is_subcon == True and self.purchase_subcon == False:
                    raise ValidationError(_("You haven't set contract subcon for this job order"))
                elif self.is_subtask == False and self.is_subcon == True and self.purchase_subcon == False and self.work_subcon_weightage == 0:
                    raise ValidationError(
                        _("You haven't set contract subcon and job subcon weightage for this job order"))
                elif self.is_subtask == False and self.purchase_subcon == False and self.work_weightage == 0 and self.work_subcon_weightage == 0:
                    raise ValidationError(
                        _("You haven't set contract subcon, job order weightage, and job subcon weightage"))
                else:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Confirmation',
                        'view_mode': 'form',
                        'target': 'new',
                        'res_model': 'in.progress.confirm.const',
                        'context': {'default_project_task_id': self.id,
                                    'default_project_id': self.project_id.id}
                    }
                    # return self.write({'state': 'inprogress', 'purchase_order_exempt' : False})

    @api.depends('is_subtask', 'stage_weightage', 'work_weightage', 'progress_task')
    def compute_contract_completion(self):
        for rec in self:
            if rec.is_subtask == False:
                rec.stage_completion = (rec.progress_task * rec.work_weightage) / 100
                rec.contract_completion = (rec.stage_completion * rec.stage_weightage) / 100
            else:
                rec.stage_completion = 0
                rec.contract_completion = 0

    @api.depends('is_subcon', 'is_subtask', 'work_subcon_weightage', 'progress_task')
    def compute_contract_completion_subcon(self):
        for rec in self:
            if rec.is_subcon == True and rec.is_subtask == False:
                rec.contract_completion_subcon = (rec.progress_task * rec.work_subcon_weightage) / 100
            else:
                rec.contract_completion_subcon = 0

    @api.onchange('project_id')
    def onchange_project_id(self):
        self.project_director = False
        self.partner_id = False
        self.sale_order = False
        self.cost_sheet = False
        self.branch_id = False
        if self.project_id:
            project = self.project_id
            self.partner_id = project.partner_id
            self.project_director = project.project_director
            self.cost_sheet = self.env['job.cost.sheet'].search(
                [('project_id', '=', project.id), ('state', 'not in', ['cancelled', 'reject', 'revised'])], limit=1)
            self.branch_id = project.branch_id.id

    @api.onchange('sale_order')
    def onchange_sale_order(self):
        self.completion_ref = False
        self.stage = False
        self.stage_new = False
        sale_stage = self.env['project.completion.const'].search(
            [('completion_id', '=', self.project_id.id), ('name', '=', self.sale_order.id)], limit=1).id
        if self.sale_order:
            self.partner_id = self.sale_order.partner_id.id
            if sale_stage:
                self.write({'completion_ref': sale_stage})
            elif not sale_stage:
                warning_mess = {
                    'message': (
                            'The work stage for contract "%s" has not yet been created. Please create contract completion stage first in the master project "%s" to continue creating this job order.' % (
                        (self.sale_order.name), (self.project_id.name))),
                    'title': "Warning"
                }
                if warning_mess != '':
                    return {'warning': warning_mess, 'value': {}}
        else:
            self.partner_id = False

    @api.onchange('purchase_subcon')
    def onchange_purchase_subcon(self):
        if self.purchase_subcon:
            purc = self.purchase_subcon
            self.sub_contractor = purc.partner_id.id

    @api.depends('completion_ref')
    def get_stages_new(self):
        for rec in self:
            if rec.completion_ref and rec.completion_ref.stage_details_ids:
                rec.stage_computed_new = [(6, 0, rec.completion_ref.stage_details_ids.ids)]
            else:
                rec.stage_computed_new = [(6, 0, [])]

    @api.onchange('is_subcon')
    def onchange_is_subcon(self):
        for res in self:
            if res.is_subcon == False:
                res.purchase_subcon = False
                res.sub_contractor = False

    def set_to_draft(self):
        for rec in self:
            if len(rec.progress_history_ids) > 0:
                raise ValidationError(_("This project is in Complete status. Therefore, it is unable to create a Job Order for this project."))
            
            project_information_ids = self.env['construction.project.information'].search([('project_task_id', '=', rec.id)])
            project_information_ids.unlink()

            active_location_ids = []
            for location in rec.active_location_ids:
                active_location_ids += [location.active_location_id.id]
            
            if len(active_location_ids) > 0:
                self.env['active.location'].search([('active_location_id', 'in', active_location_ids)]).unlink()

            rec.write({
                'state': 'draft',
            })
            if not rec.is_subtask:
                for labour in rec.labour_usage_ids:
                    if rec.cost_sheet:
                        labour.cs_labour_id.reserved_time -= labour.time
                        labour.cs_labour_id.reserved_contractors -= labour.contractors
                        labour.cs_labour_id.reserved_amt -= labour.contractors * labour.unit_price * labour.time

                        if labour.bd_labour_id:
                            labour.bd_labour_id.reserved_time -= labour.time
                            labour.bd_labour_id.reserved_contractors -= labour.contractors
                            labour.bd_labour_id.amt_res -= labour.contractors * labour.unit_price * labour.time
                if rec.cost_sheet:
                    if rec.cost_sheet.budgeting_method == 'gop_budget':
                        rec.cost_sheet.get_gop_labour_table()
                        if rec.project_budget:
                            rec.project_budget.get_gop_labour_table()

    @api.depends('progress_history_ids.progress', 'progress_history_ids.approved_progress')
    def compute_progress_task(self):
        progress = 0
        for res in self:
            if res.is_progress_history_approval_matrix == False:
                progress = sum(res.progress_history_ids.mapped('progress'))
            else:
                progress = sum(res.progress_history_ids.mapped('approved_progress'))
            res.progress_task = progress
        return progress

    def _compute_product_usage(self):
        for rec in self:
            product_usage_count = self.env['stock.scrap.request'].search_count([('work_orders', '=', self.id)])
            rec.total_product_usage = product_usage_count

    def _compute_asset_allocation(self):
        for rec in self:
            asset_allocation_count = self.env['allocation.asset.line'].search_count([('job_order', '=', self.id)])
            rec.total_asset_allocation = asset_allocation_count

    @api.onchange('sub_contractor')
    def onchange_sub_contractor(self):
        for record in self:
            automated_id = self.env['account.analytic.line'].search([('task_id', '=', record.name)])
            for result in automated_id:
                result.write({'is_subcon': record.is_subcon})
                result.write({'subcon_id': record.sub_contractor})

    @api.model
    def create(self, vals):
        project_obj = self.env['project.project'].browse(vals.get('project_id'))
        if project_obj.primary_states == 'completed':
            raise ValidationError(
                _("This project is in Complete status. Therefore, it is unable to create a Job Order for this project."))
        else:
            vals['number'] = self.env['ir.sequence'].next_by_code('project.task.sequence')
            return super(ProjectTaskNew, self).create(vals)

    @api.onchange('worker_assigned_to')
    def onchange_worker_assigned_to(self):
        for rec in self:
            for pic in rec.worker_assigned_to:
                rec.employee_worker_ids = [(4, pic.id)]
                for worker in rec.employee_worker_ids:
                    pic_ids = rec.worker_assigned_to._origin.ids
                    if worker._origin.id not in rec.labour_usage_ids.mapped('workers_ids')._origin.ids:
                        if len(pic_ids) > 0:
                            if worker._origin.id not in pic_ids:
                                rec.employee_worker_ids = [(3, worker.id)]
                        else:
                            rec.employee_worker_ids = [(3, worker.id)]

    @api.onchange('labour_usage_ids')
    def onchange_labour_usage_worker(self):
        for rec in self:
            for labour in rec.labour_usage_ids:
                if labour.workers_ids:
                    for worker in labour.workers_ids:
                        rec.employee_worker_ids = [(4, worker.id)]
            for worker in rec.employee_worker_ids:
                if worker._origin.id not in rec.worker_assigned_to.ids:
                    workers_ids = rec.labour_usage_ids.mapped('workers_ids')._origin.ids
                    if len(workers_ids) > 0:
                        if worker._origin.id not in workers_ids:
                            rec.employee_worker_ids = [(3, worker.id)]
                    else:
                        rec.employee_worker_ids = [(3, worker.id)]

    def unlink(self):
        for res in self:
            subtsk = self.env['project.subtask'].search([('name', '=', res.name)])
            subtsk.unlink()
        return super(ProjectTaskNew, self).unlink()

    @api.depends('project_id')
    def get_stages(self):
        for rec in self:
            if rec.project_id and rec.project_id.stage_ids:
                rec.stage_computed = [(6, 0, rec.project_id.stage_ids.ids)]
            else:
                rec.stage_computed = [(6, 0, [])]

    @api.onchange('stage_new')
    def onchange_stage_weightage(self):
        self.stage_weightage = False
        if self.stage_new:
            sta = self.stage_new
            self.stage_weightage = sta.stage_weightage

    @api.depends('stage_new')
    def depends_stage_new(self):
        if self.stage_new:
            self.parent_task = self.self_new.parent_task.id
        else:
            self.parent_task = False

    @api.onchange('job_estimate')
    def onchange_job_estimate(self):
        self.completion_ref = False
        self.stage = False
        self.stage_new = False
        sale_stage = self.env['project.completion.const'].search(
            [('completion_id', '=', self.project_id.id), ('job_estimate', '=', self.job_estimate.id)], limit=1).id
        if self.job_estimate:
            if sale_stage:
                self.write({'completion_ref': sale_stage})
            elif not sale_stage:
                warning_mess = {
                    'message': (
                            'The work stage for contract "%s" has not yet been created. Please create contract completion stage first in the master project "%s" to continue creating this job order.' % (
                        (self.job_estimate.name), (self.project_id.name))),
                    'title': "Warning"
                }
                if warning_mess != '':
                    return {'warning': warning_mess, 'value': {}}

    def action_complete(self):
        dates = list()
        for rec in self.progress_history_ids:
            dates.append(rec.progress_end_date_new)
        if len(dates) > 0:
            latest_end_date = max(dates)
        else:
            latest_end_date = datetime.now()

        issue = self.env['project.issue'].search(
            [('project_id', '=', self.project_id.id), ('job_order_id', '=', self.id),
             ('state', 'not in', ['solved', 'cancelled'])])
        if len(issue) > 0:
            raise ValidationError(
                _("Unable to complete this job order because there are still issues related to this job order. please solve the issue first"))
        else:
            if self.progress_task < 100:
                context = {'default_actual_end_date': latest_end_date,
                           'default_project_task_id': self.id, }
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'complete.confirm.wiz',
                    'name': _("Completion Validation"),
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'context': context,
                }

            else:
                context = {'default_actual_end_date': latest_end_date,
                           'default_project_task_id': self.id, }
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'project.task.completion.wizard',
                'name': _("Completion Confirmation"),
                'target': 'new',
                'view_type': 'form',
                'view_mode': 'form',
                'context': context,
            }

    def create_subtask(self):
        subtask_weightage = 0
        weightage_final = 0
        progress = self.progress_task
        subtask = self.env['project.task'].search(
            [('project_id', '=', self.project_id.id), ('parent_task', '=', self.id)])

        if subtask:
            for sub in subtask:
                subtask_weightage += sub.work_subtask_weightage
        else:
            subtask_weightage = 0

        weightage_final = progress + subtask_weightage

        if weightage_final >= 100:
            raise ValidationError(
                _("Cannot add subtask because job weightage for this job order is already assigned or fully allocated."))

        context = {'default_parent_task': self.id}
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'create.subtask.wiz',
            'name': _("Create Subtasks"),
            "context": context,
            'target': 'new',
            'view_type': 'form',
            'view_mode': 'form',
        }

    def product_usage(self):
        context = {
            'default_project_id': self.project_id.id,
            'default_warehouse': self.project_id.warehouse_address.id,
            'default_analytic_groups': self.project_id.analytic_idz.id,
            'default_job_order': self.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.usage.wiz',
            'name': _("Create Material Usage"),
            "context": context,
            'target': 'new',
            'view_type': 'form',
            'view_mode': 'form',
        }

    def action_product_usage(self):
        return {
            'name': ("Material Usage"),
            'view_mode': 'tree,form',
            'res_model': 'stock.scrap.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('work_orders', '=', self.id)],
        }

    def action_asset_allocation(self):
        return {
            'name': ("Asset Allocation"),
            'view_mode': 'tree,form',
            'res_model': 'allocation.asset.line',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('job_order', '=', self.id)],
        }

    def get_labour_usage(self):
        for rec in self:
            vals = []
            for labour in rec.labour_usage_ids:
                if labour.time_left > 0:
                    vals.append((0, 0, {
                        'labour_usage_line_id': labour.id,
                        'project_task_id': rec.id,
                        'cs_labour_id': labour.cs_labour_id.id,
                        'bd_labour_id': labour.bd_labour_id.id,
                        'project_scope_id': labour.project_scope_id.id,
                        'section_id': labour.section_id.id,
                        'group_of_product_id': labour.group_of_product_id.id,
                        'product_id': labour.product_id.id,
                        'contractors': labour.contractors,
                        'temp_time_left': labour.time,
                        # 'time': labour.time,
                        # 'time_left': labour.time_left,
                        'uom_id': labour.uom_id.id,
                        'unit_price': labour.unit_price,
                        'workers_ids': [(6, 0, labour.workers_ids.ids)],
                        'analytic_group_ids': [(6, 0, rec.cost_sheet.account_tag_ids.ids)]
                    }))
            return vals

    def create_progress_history(self):
        # add validation when “add a progress” if history progress has not been accepted or rejected
        progress_ids = self.progress_history_ids.filtered(
            lambda f: f.state in ['draft', 'to_approve'])
        if len(progress_ids) > 0:
            raise ValidationError(
                _("Cannot add progress anymore because request status waiting for approval in progress history."))
        context = {'default_work_order': self.id,
                   'default_name': self.name,
                   'default_project_id': self.project_id.id,
                   'default_sale_order': self.sale_order.id,
                   'default_purchase_subcon': self.purchase_subcon.id,
                   'default_completion_ref': self.completion_ref.id,
                   'default_stage_new': self.stage_new.id,
                   'default_is_subcon': self.is_subcon,
                   'default_is_subtask': self.is_subtask,
                   'default_subtask_exist': self.subtask_exist,
                   'default_job_estimate': self.job_estimate.id,
                   'default_branch_id': self.branch_id.id,
                   'default_parent_task': self.parent_task.id,
                   'default_labour_usage_ids': self.get_labour_usage(),
                   }

        if self.state != 'inprogress':
            raise ValidationError(
                _("Cannot add progress when state is not in 'Progress'.\nClick In Progress button first"))
        elif self.progress_task == 100:
            raise ValidationError(
                _("Cannot add progress anymore because the progress of this job order is already 100%"))
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'progress.history.wiz',
                'name': _("Create Progress History"),
                "context": context,
                'target': 'new',
                'view_type': 'form',
                'view_mode': 'form',
            }

    @api.onchange('progress_history_ids')
    def _onchange_validate_delete(self):
        for record in self:
            if record.is_subtask:
                if len(record.progress_history_ids) > 0:
                    history_list = list()
                    remaining_local_history_list = list()

                    for progress in self.env['progress.history'].search([('work_order', '=', self.id.origin)]):
                        history_list.append(progress)

                    for remaining in record.progress_history_ids:
                        remaining_local_history_list.append(remaining)

                    # difference total record between remaining local and progress in database used to compare data sequence
                    diff_record_amount = abs(len(remaining_local_history_list) - len(history_list))

                    # to check if the change made in progress_history_ids is delete
                    if len(remaining_local_history_list) < len(history_list):
                        if remaining_local_history_list[0].id.origin != history_list[diff_record_amount].id:
                            raise ValidationError(_("You must delete records sequentially."))

            else:
                if len(record.progress_history_ids) > 0:
                    if self.subtask_exist:
                        history_list = list()
                        remaining_local_history_list = list()

                        for progress in self.env['progress.history'].search([('work_order', '=', self.id.origin)]):
                            history_list.append(progress)

                        for remaining in record.progress_history_ids:
                            remaining_local_history_list.append(remaining)

                        # difference total record between remaining local and progress in database used to compare data sequence
                        diff_record_amount = abs(len(remaining_local_history_list) - len(history_list))

                        # to check if the change made in progress_history_ids is delete
                        if len(remaining_local_history_list) < len(history_list):
                            if remaining_local_history_list[0].id.origin != history_list[diff_record_amount].id:
                                raise ValidationError(_("You must delete records sequentially."))

                        # history_list = {}
                        # remaining_local_history_list = {}
                        # subtasks= self.env['project.task'].search([('parent_task', '=', self.id.origin)])

                        # # to group progress history by subtask
                        # for remaining in record.progress_history_ids:
                        #     for sub in subtasks:
                        #         if sub.name in remaining_local_history_list:
                        #             if remaining.subtask.name == sub.name:
                        #                 remaining_local_history_list[sub.name].append(remaining)
                        #             else:
                        #                 continue
                        #         elif sub.name not in remaining_local_history_list:
                        #             if remaining.subtask.name == sub.name:
                        #                 remaining_local_history_list[sub.name] = [remaining]
                        #             else:
                        #                 continue

                        # validate = []
                        # for sub in subtasks:
                        #     if sub.name in remaining_local_history_list:
                        #         validate.append(self._validate_delete_progress_subtask(sub, remaining_local_history_list[sub.name]))

                        # if False in validate:
                        #     raise ValidationError(_("You must delete records sequentially."))

                    else:
                        history_list = list()
                        remaining_local_history_list = list()

                        for progress in self.env['progress.history'].search([('work_order', '=', self.id.origin)]):
                            history_list.append(progress)

                        for remaining in record.progress_history_ids:
                            remaining_local_history_list.append(remaining)

                        # difference total record between remaining local and progress in database used to compare data sequence
                        diff_record_amount = abs(len(remaining_local_history_list) - len(history_list))

                        # to check if the change made in progress_history_ids is delete
                        if len(remaining_local_history_list) < len(history_list):
                            if remaining_local_history_list[0].id.origin != history_list[diff_record_amount].id:
                                raise ValidationError(_("You must delete records sequentially."))

    def _validate_delete_progress_subtask(self, subtask, remaining_local_history_list):

        if len(remaining_local_history_list) > 0:
            history_list = list()

            for progress in self.env['progress.history'].search([('work_order', '=', subtask.id)]):
                history_list.append(progress)

            diff_record_amount = abs(len(remaining_local_history_list) - len(history_list))

            # to check if the change made in progress_history_ids is delete
            if len(remaining_local_history_list) < len(history_list):
                if remaining_local_history_list[0].progress_start_date_new != history_list[
                    diff_record_amount].progress_start_date_new and remaining_local_history_list[
                    0].progress_end_date_new != history_list[diff_record_amount].progress_end_date_new and \
                        remaining_local_history_list[0].progress_summary != history_list[
                    diff_record_amount].progress_summary:
                    return False

        return True


class TaskProductCons(models.Model):
    _name = 'task.product.cons'
    _description = "Task Product Planning"
    _order = 'sequence'

    task_product_id = fields.Many2one('project.task', string='Job Order')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    number = fields.Char(string='ID', related='task_product_id.number')
    date = fields.Date(string="Date", default=date.today())
    task_product_material = fields.One2many('task.product.material', 'task_planning_id')
    task_product_labour = fields.One2many('task.product.labour', 'task_planning_id')
    task_product_overhead = fields.One2many('task.product.overhead', 'task_planning_id')
    project_scope = fields.Many2many('project.scope.line', string='Project Scope')
    section_name = fields.Many2many('section.line', string='Section')
    subtotal = fields.Float(string='Subtotal')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirm', 'Confirmed'),
        ('revise', 'Revised')
    ], string="Status", default='draft')

    @api.depends('task_product_id.task_product_ids', 'task_product_id.task_product_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.task_product_id.task_product_ids:
                no += 1
                l.sr_no = no

    # @api.depends('task_product_material.subtotal', 'task_product_labour.subtotal', 'task_product_overhead.subtotal')
    # def _onchange_calculate_total(self):
    #     for task in self:
    #         total = 0.0
    #         if task.task_product_material:
    #             for line in task.task_product_material:
    #                 material_price = (line.quantity * line.unit_price)
    #                 total += material_price

    #         if task.task_product_labour:
    #             for line in task.task_product_labour:
    #                 labour_price = (line.quantity * line.unit_price)
    #                 total += labour_price

    #         if task.task_product_overhead:
    #             for line in task.task_product_overhead:
    #                 overhead_price = (line.quantity * line.unit_price)
    #                 total += overhead_price

    #         task.subtotal += total


class TaskProductMaterials(models.Model):
    _name = 'task.product.material'
    _description = "Task Product Material"
    _order = 'sequence'

    task_planning_id = fields.Many2one('task.product.cons', string='Planning')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Text('Description')
    quantity = fields.Float(string="Quantity Used", default=0.00)
    quantity_left = fields.Float(string="Quantity Left", default=0.00)
    budget_quantity = fields.Float(string="Budget Quantity", default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float('Unit Price', default=0.0)
    subtotal = fields.Float('Subtotal', readonly=True)

    @api.depends('task_planning_id.task_product_material', 'task_planning_id.task_product_material.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.task_planning_id.task_product_material:
                no += 1
                l.sr_no = no

    # @api.onchange('quantity', 'unit_price')
    # def onchange_quantity(self):
    #     price = 0.0
    #     for line in self:
    #         price = (line.quantity * line.unit_price) 
    #         line.subtotal = price


class TaskProductLabour(models.Model):
    _name = 'task.product.labour'
    _description = "Task Product Labour"
    _order = 'sequence'

    task_planning_id = fields.Many2one('task.product.cons', string='Planning')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Text('Description')
    quantity = fields.Float(string="Quantity Used", default=0.00)
    quantity_left = fields.Float(string="Quantity Left", default=0.00)
    budget_quantity = fields.Float(string="Budget Quantity", default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float('Unit Price', default=0.0)
    subtotal = fields.Float('Subtotal', readonly=True)

    @api.depends('task_planning_id.task_product_labour', 'task_planning_id.task_product_labour.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.task_planning_id.task_product_labour:
                no += 1
                l.sr_no = no

    # @api.onchange('quantity', 'unit_price')
    # def onchange_quantity(self):
    #     price = 0.0
    #     for line in self:
    #         price = (line.quantity * line.unit_price) 
    #         line.subtotal = price


class TaskProductOverhead(models.Model):
    _name = 'task.product.overhead'
    _description = "Task Product Overhead"
    _order = 'sequence'

    task_planning_id = fields.Many2one('task.product.cons', string='Planning')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Text('Description')
    quantity = fields.Float(string="Quantity Used", default=0.00)
    quantity_left = fields.Float(string="Quantity Left", default=0.00)
    budget_quantity = fields.Float(string="Budget Quantity", default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float('Unit Price', default=0.0)
    subtotal = fields.Float('Subtotal', readonly=True)

    @api.depends('task_planning_id.task_product_overhead', 'task_planning_id.task_product_overhead.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.task_planning_id.task_product_overhead:
                no += 1
                l.sr_no = no

    # @api.onchange('quantity', 'unit_price')
    # def onchange_quantity(self):
    #     price = 0.0
    #     for line in self:
    #         price = (line.quantity * line.unit_price) 
    #         line.subtotal = price


class ConsumedMaterials(models.Model):
    _name = 'consumed.material'
    _description = "Consumed Materials"
    _order = 'sequence'
    _check_company_auto = True

    consumed_id = fields.Many2one('project.task', string='Work Order')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product',
                                 check_company=True, required=True)
    company_id = fields.Many2one(related='consumed_id.company_id', string='Company', readonly=True)
    description = fields.Text('Description')
    quantity = fields.Float(string="Quantity Used", default=0.00)
    quantity_left = fields.Float(string="Quantity Left", default=0.00)
    budget_quantity = fields.Float(string="Budget Quantity", default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')

    @api.depends('consumed_id.consumed_material_ids', 'consumed_id.consumed_material_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.consumed_id.consumed_material_ids:
                no += 1
                l.sr_no = no

    @api.model
    @api.constrains('quantity')
    def _check_quantity(self):
        for material in self:
            if not material.quantity > 0.00:
                raise ValidationError(
                    _('Quantity of material consumed must be greater than 0.')
                )

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.description = self.product_id.name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = False


class ConsumedEquipment(models.Model):
    _name = 'consumed.equipment'
    _description = "Consumed Equipment"
    _order = 'sequence'
    _check_company_auto = True

    consumed_id = fields.Many2one('project.task', string='Work Order')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product',
                                 check_company=True, required=True)
    company_id = fields.Many2one(related='consumed_id.company_id', string='Company', readonly=True)
    description = fields.Text('Description')
    quantity = fields.Float(string="Quantity Used", default=0.00)
    quantity_left = fields.Float(string="Quantity Left", default=0.00)
    budget_quantity = fields.Float(string="Budget Quantity", default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')

    @api.depends('consumed_id.consumed_equipment_ids', 'consumed_id.consumed_equipment_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.consumed_id.consumed_equipment_ids:
                no += 1
                l.sr_no = no

    @api.model
    @api.constrains('quantity')
    def _check_quantity(self):
        for material in self:
            if not material.quantity > 0.00:
                raise ValidationError(
                    _('Quantity of material consumed must be greater than 0.')
                )

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.description = self.product_id.name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = False


class ConsumedLabour(models.Model):
    _name = 'consumed.labour'
    _description = "Consumed Labour"
    _order = 'sequence'
    _check_company_auto = True

    consumed_id = fields.Many2one('project.task', string='Work Order')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product',
                                 check_company=True, required=True)
    company_id = fields.Many2one(related='consumed_id.company_id', string='Company', readonly=True)
    description = fields.Text('Description')
    quantity = fields.Float(string="Quantity Used", default=0.00)
    quantity_left = fields.Float(string="Quantity Left", default=0.00)
    budget_quantity = fields.Float(string="Budget Quantity", default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')

    @api.depends('consumed_id.consumed_labour_ids', 'consumed_id.consumed_labour_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.consumed_id.consumed_labour_ids:
                no += 1
                l.sr_no = no

    @api.model
    @api.constrains('quantity')
    def _check_quantity(self):
        for material in self:
            if not material.quantity > 0.00:
                raise ValidationError(
                    _('Quantity of material consumed must be greater than 0.')
                )

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.description = self.product_id.name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = False


class ConsumedOverhead(models.Model):
    _name = 'consumed.overhead'
    _description = "Consumed Overhead"
    _order = 'sequence'
    _check_company_auto = True

    consumed_id = fields.Many2one('project.task', string='Work Order')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product',
                                 check_company=True, required=True)
    company_id = fields.Many2one(related='consumed_id.company_id', string='Company', readonly=True)
    description = fields.Text('Description')
    quantity = fields.Float(string="Quantity Used", default=0.00)
    quantity_left = fields.Float(string="Quantity Left", default=0.00)
    budget_quantity = fields.Float(string="Budget Quantity", default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')

    @api.depends('consumed_id.consumed_overhead_ids', 'consumed_id.consumed_overhead_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.consumed_id.consumed_overhead_ids:
                no += 1
                l.sr_no = no

    @api.model
    @api.constrains('quantity')
    def _check_quantity(self):
        for material in self:
            if not material.quantity > 0.00:
                raise ValidationError(
                    _('Quantity of material consumed must be greater than 0.')
                )

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.description = self.product_id.name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = False


class ProjectSubtasks(models.Model):
    _name = 'project.subtask'
    _description = "Subtasks"
    _order = 'sequence'

    subtask_id = fields.Many2one('project.task', string='Work Order', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    name = fields.Char(string="Subtask", required="1")
    description = fields.Text(string="Subtask Description")
    assigned_to = fields.Many2one('res.users', string="PIC")
    assigned_date = fields.Datetime(string="Assigned Date")
    planned_hour = fields.Float(string="Planned Hours")
    actual_hour = fields.Float(string="Actual Hours")
    remaining_hour = fields.Float(string="Remaining Hours")
    progress_completion = fields.Float(string="Progress Completion (%)")
    work_subtask_weightage = fields.Float(string="Subtask Weightage")

    @api.depends('subtask_id.subtask_ids', 'subtask_id.subtask_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.subtask_id.subtask_ids:
                no += 1
                l.sr_no = no


class ConsumedHistory(models.Model):
    _name = 'consumed.history'
    _description = "Consumed History"
    _order = 'sequence'

    consumed_id = fields.Many2one('project.task', string='Work Order', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    usage_id = fields.Many2one('stock.scrap.request', string='Work Order', ondelete='cascade')
    date_used = fields.Datetime(string="Date")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product', check_company=True, required=True)
    quantity = fields.Float(string="Quantity")
    company_id = fields.Many2one(related='consumed_id.company_id', string='Company', readonly=True)
    material_type = fields.Selection(
        [('material', 'Material'), ('equipment', 'Equipment'), ('labour', 'Labour'), ('overhead', 'Overhead')],
        string="Material Type")


class ConsumedMaterialHistory(models.Model):
    _name = 'consumed.material.history'
    _description = "Consumed Material History"
    _order = 'sequence'

    consumed_id = fields.Many2one('project.task', string='Work Order', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    usage_id = fields.Many2one('stock.scrap.request', string='Material Usage', ondelete='cascade')
    date_used = fields.Datetime(string="Date")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product', check_company=True)
    quantity = fields.Float(string="Quantity")
    company_id = fields.Many2one(related='consumed_id.company_id', string='Company', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('validated', 'Validated'),
        ('cancel', 'Cancelled')
    ], string='State')

    @api.depends('consumed_id.consumed_material_history_ids', 'consumed_id.consumed_material_history_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.consumed_id.consumed_material_history_ids:
                no += 1
                l.sr_no = no


class ConsumedEquipmentHistory(models.Model):
    _name = 'consumed.equipment.history'
    _description = "Consumed Equipment History"
    _order = 'sequence'

    consumed_id = fields.Many2one('project.task', string='Work Order', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    usage_id = fields.Many2one('stock.scrap.request', string='Material Usage', ondelete='cascade')
    date_used = fields.Datetime(string="Date")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product', check_company=True, required=True)
    quantity = fields.Float(string="Quantity")
    company_id = fields.Many2one(related='consumed_id.company_id', string='Company', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('validated', 'Validated'),
        ('cancel', 'Cancelled')
    ], string='State')

    @api.depends('consumed_id.consumed_equipment_history_ids', 'consumed_id.consumed_equipment_history_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.consumed_id.consumed_equipment_history_ids:
                no += 1
                l.sr_no = no


class ConsumedLabourHistory(models.Model):
    _name = 'consumed.labour.history'
    _description = "Consumed Labour History"
    _order = 'sequence'

    consumed_id = fields.Many2one('project.task', string='Work Order', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    usage_id = fields.Many2one('stock.scrap.request', string='Material Usage', ondelete='cascade')
    date_used = fields.Datetime(string="Date")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product', check_company=True, required=True)
    quantity = fields.Float(string="Quantity")
    company_id = fields.Many2one(related='consumed_id.company_id', string='Company', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('validated', 'Validated'),
        ('cancel', 'Cancelled')
    ], string='State')

    @api.depends('consumed_id.consumed_labour_history_ids', 'consumed_id.consumed_labour_history_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.consumed_id.consumed_labour_history_ids:
                no += 1
                l.sr_no = no


class ConsumedOverheadHistory(models.Model):
    _name = 'consumed.overhead.history'
    _description = "Consumed Overhead History"
    _order = 'sequence'

    consumed_id = fields.Many2one('project.task', string='Work Order', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    usage_id = fields.Many2one('stock.scrap.request', string='Material Usage', ondelete='cascade')
    date_used = fields.Datetime(string="Date")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product', check_company=True, required=True)
    quantity = fields.Float(string="Quantity")
    company_id = fields.Many2one(related='consumed_id.company_id', string='Company', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('validated', 'Validated'),
        ('cancel', 'Cancelled')
    ], string='State')

    @api.depends('consumed_id.consumed_overhead_history_ids', 'consumed_id.consumed_overhead_history_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.consumed_id.consumed_overhead_history_ids:
                no += 1
                l.sr_no = no


class ProgressHistory(models.Model):
    _name = 'progress.history'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _rec_name = 'number'
    _description = "Progress History"
    _order = 'progress_start_date_new DESC'

    # @api.model
    # def create(self, vals):
    #     if vals.get('number', 'New') == 'New':
    #         vals['number'] = self.env['ir.sequence'].next_by_code('progress.history.sequence') or '/'
    #     res = super(ProgressHistory, self).create(vals)
    #     return res

    active = fields.Boolean(related="work_order.active", string='Active')
    number = fields.Char(string='Number', copy=False, required=True, readonly=True, index=True)
    work_order = fields.Many2one('project.task', string='Work Order', ondelete='restrict')
    name = fields.Char(related="work_order.name", string='Work Order')
    project_id = fields.Many2one(related="work_order.project_id", string="Project")
    sale_order = fields.Many2one(related="work_order.sale_order", string="Contract")
    purchase_subcon = fields.Many2one(related="work_order.purchase_subcon", string="Contract")
    completion_ref = fields.Many2one(related="work_order.completion_ref", string="Contract")
    date_create = fields.Datetime(string="Creation date", readonly=True)
    create_by = fields.Many2one('res.users', index=True, readonly=True)
    stage_computed_new = fields.Many2many('project.stage.const', 'stage_rel', string='Stages')
    stage_new = fields.Many2one(related="work_order.stage_new", string="Stage")
    stage = fields.Many2one(related="work_order.stage", string="Stage")
    progress_start_date = fields.Date(string='Progress Start Date')
    progress_end_date = fields.Date(string='Progress End Date')
    progress_start_date_new = fields.Datetime(string='Progress Start Date')
    progress_end_date_new = fields.Datetime(string='Progress End Date')
    progress = fields.Float(string="Additional Progress (%)")
    approved_progress = fields.Float(string="Approved Progress (%)")
    progress_subtask = fields.Float(string="Additional Progress Subtask (%)")
    progress_summary = fields.Text(string='Progress Summary')
    attachment_ids = fields.One2many('attachment.file', 'progress')
    latest_completion = fields.Float(string="Latest Completion (%)")
    latest_completion_subtask = fields.Float(string="Latest Completion Subtask (%)")
    is_subcon = fields.Boolean(related="work_order.is_subcon")
    subtask = fields.Many2one('project.task', string='Subtask',
                              domain="[('is_subtask', '=', True), ('project_id', '=', parent.project_id), ('sale_order', '=', parent.sale_order), ('stage_new', '=', parent.stage_new), ('parent_task.name', '=', parent.name), ('state', '=', 'inprogress')]")
    subtask_exist = fields.Boolean(related="work_order.subtask_exist")
    subtask_parents = fields.Text(string='Subtask Parent(s)', compute='_get_subtask_parents')
    hide_subtask_parents = fields.Boolean(string='Hide Subtask Parent(s)', default=True,
                                          compute='_get_hide_subtask_parents')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string="Request Status", tracking=True, default='draft')
    state_2 = fields.Selection(related="state", string="Request Status")
    company_id = fields.Many2one(related="work_order.company_id", string="Company")
    branch_id = fields.Many2one(related="work_order.branch_id", string="Branch")
    is_subtask = fields.Boolean(related="work_order.is_subtask", string="Is a Subtask")
    progress_wiz = fields.Many2one('progress.history.wiz', string="Progress Wizard")
    parent_task = fields.Many2one(related='work_order.parent_task', string="Parent Task")
    custom_project_progress = fields.Selection(related='work_order.custom_project_progress',
                                               string='Custom Project Progress')
    labour_usage_ids = fields.One2many('progress.history.labour.usage', 'progress_history_id', string='Labour Usage')
    is_job_order_complete = fields.Boolean(string='Job Order Complete', compute='_compute_is_job_order_complete')
    is_using_labour_attendance = fields.Boolean(related='project_id.is_using_labour_attendance')
    account_move_id = fields.Many2one(related='progress_wiz.account_move_id')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))

        return super(ProgressHistory, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))
        return super(ProgressHistory, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                       orderby=orderby, lazy=lazy)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ProgressHistory, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
            'abs_construction_management.group_construction_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)

        return res

    def cancel_labour_usage(self):
        for rec in self:
            # get all task and subtask
            project_task = rec.work_order
            parent_task = False
            is_subtask_exist = False
            if not project_task.is_subtask:
                parent_task = project_task
            else:
                parent_task = rec.work_order._get_subtask_parents()
                is_subtask_exist = True

            if not is_subtask_exist:
                rec.progress_wiz.account_move_id.unlink()
                # return labour usage time value based on time usage
                for labour in parent_task.progress_history_ids.filtered(lambda x: x.progress_wiz.id == rec.progress_wiz.id).labour_usage_ids:
                    actual_used_amount = labour.time_usage * labour.contractors * labour.unit_price
                    labour.labour_usage_line_id.time += labour.time_usage

                    labour.cs_labour_id.actual_used_time -= labour.time_usage
                    labour.cs_labour_id.actual_used_amt -= actual_used_amount
                    labour.cs_labour_id.reserved_time += labour.time_usage
                    labour.cs_labour_id.reserved_amt += actual_used_amount
                    if labour.bd_labour_id:
                        labour.bd_labour_id.time_used -= labour.time_usage
                        labour.bd_labour_id.amt_used -= actual_used_amount
                        labour.bd_labour_id.reserved_time += labour.time_usage
                        labour.bd_labour_id.amt_res += actual_used_amount
                return
            else:
                subtasks = parent_task._get_subtask(depth=0)
                rec.progress_wiz.account_move_id.unlink()
                # return labour usage time value of all related task/subtask based on time usage
                for labour in parent_task.progress_history_ids.filtered(lambda x: x.progress_wiz.id == rec.progress_wiz.id).labour_usage_ids:
                    actual_used_amount = labour.time_usage * labour.contractors * labour.unit_price
                    labour.labour_usage_line_id.time += labour.time_usage

                    labour.cs_labour_id.actual_used_time -= labour.time_usage
                    labour.cs_labour_id.actual_used_amt -= actual_used_amount
                    labour.cs_labour_id.reserved_time += labour.time_usage
                    labour.cs_labour_id.reserved_amt += actual_used_amount
                    if labour.bd_labour_id:
                        labour.bd_labour_id.time_used -= labour.time_usage
                        labour.bd_labour_id.amt_used -= actual_used_amount
                        labour.bd_labour_id.reserved_time += labour.time_usage
                        labour.bd_labour_id.amt_res += actual_used_amount
                    for task in subtasks:
                        if len(task.labour_usage_ids) > 0:
                            if task.cost_sheet.budgeting_period in ['project', 'custom']:
                                task_labour_line = task.labour_usage_ids.filtered(
                                    lambda x: x.bd_labour_id.id == labour.labour_usage_line_id.bd_labour_id.id)
                                task_labour_line.time += labour.time_usage
                            elif task.cost_sheet.budgeting_period == 'project':
                                task_labour_line = task.labour_usage_ids.filtered(
                                    lambda x: x.bd_labour_id.id == labour.labour_usage_line_id.cs_labour_id.id)
                                task_labour_line.time += labour.time_usage
            return

    def unlink(self):
        for rec in self:
            if rec.account_move_id:
                if rec.account_move_id.state == 'posted':
                    raise ValidationError(_("You're not allowed to delete progress history when "
                                            "its labour bill's state is posted."))

            # need to only run once
            if not self.env.context.get('from_subtask') and not self.env.context.get('from_parent'):
                if rec.is_progress_history_approval_matrix:
                    if rec.state == 'approved':
                        rec.cancel_labour_usage()
                else:
                    rec.cancel_labour_usage()

            # If deleted from parent task
            if rec.work_order.is_subtask == False and not self.env.context.get('from_subtask'):
                if rec.work_order.subtask_exist:
                    progress_history = False
                    bottom_progress_history = False

                    if rec.subtask:
                        progress_history = rec.env['progress.history'].search([
                            ('id', '!=', rec.id),  #prevent missing record error
                            ('subtask', '=', rec.subtask.id),
                            ('progress_start_date_new', '=', rec.progress_start_date_new),
                            ('progress_end_date_new', '=', rec.progress_end_date_new),
                            ('progress_summary', '=', rec.progress_summary)])
                        bottom_progress_history = rec.env['progress.history'].search([
                            ('id', '!=', rec.id),
                            ('work_order', '=', rec.subtask.id),
                            ('progress_start_date_new', '=', rec.progress_start_date_new),
                            ('progress_end_date_new', '=', rec.progress_end_date_new),
                            ('progress_summary', '=', rec.progress_summary)], limit=1)

                        deleteable_progress = progress_history + bottom_progress_history
                        if deleteable_progress and not self.env.context.get('progress_deleted'):
                            deleteable_progress.with_context({'progress_deleted': True,
                                                              'from_parent': True}).unlink()
                    else:
                        return super(ProgressHistory, self).unlink()

            # # If deleted from subtask
            elif rec.work_order.is_subtask and not self.env.context.get('from_parent'):
                progress_history = False
                bottom_progress_history = False
                if rec.subtask and not self.env.context.get('subtask_empty'):
                    progress_history = rec.env['progress.history'].search([
                        ('id', '!=', rec.id),  #prevent missing record error
                        ('subtask', '=', rec.subtask.id), ('progress_start_date_new', '=', rec.progress_start_date_new),
                        ('progress_end_date_new', '=', rec.progress_end_date_new),
                        ('progress_summary', '=', rec.progress_summary)])
                    bottom_progress_history = rec.env['progress.history'].search([
                        ('id', '!=', rec.id),  # prevent missing record error
                        ('work_order', '=', rec.subtask.id),
                        ('progress_start_date_new', '=', rec.progress_start_date_new),
                        ('progress_end_date_new', '=', rec.progress_end_date_new),
                        ('progress_summary', '=', rec.progress_summary)], limit=1)

                    deleteable_progress = progress_history + bottom_progress_history
                    if deleteable_progress and not self.env.context.get('progress_deleted'):
                        deleteable_progress.with_context({'progress_deleted': True,
                                                          'has_subtask': True,
                                                          'from_subtask': True}).unlink()

                elif not rec.subtask and not self.env.context.get('has_subtask'):
                    progress_history = rec.env['progress.history'].search([
                        ('id', '!=', rec.id),  #prevent missing record error
                        ('subtask', '=', rec.work_order.id),
                        ('progress_start_date_new', '=', rec.progress_start_date_new),
                        ('progress_end_date_new', '=', rec.progress_end_date_new),
                        ('progress_summary', '=', rec.progress_summary)])
                    bottom_progress_history = rec.env['progress.history'].search([
                        ('id', '!=', rec.id),  # prevent missing record error
                        ('work_order', '=', rec.subtask.id),
                        ('progress_start_date_new', '=', rec.progress_start_date_new),
                        ('progress_end_date_new', '=', rec.progress_end_date_new),
                        ('progress_summary', '=', rec.progress_summary)], limit=1)

                    deleteable_progress = progress_history + bottom_progress_history
                    if deleteable_progress and not self.env.context.get('progress_deleted'):
                        deleteable_progress.with_context({'progress_deleted': True,
                                                          'subtask_empty': True,
                                                          'from_subtask': True}).unlink()

        return super(ProgressHistory, self).unlink()

    def delete_progress(self):
        for rec in self:
            if rec.account_move_id:
                if rec.account_move_id.state == 'posted':
                    raise ValidationError(_("You're not allowed to delete progress history when "
                                            "its labour bill's state is posted."))

            action = {
                'name': 'Delete Confirmation',
                'type': 'ir.actions.act_window',
                'res_model': 'progress.history.deletion.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_current_progress': rec.id,
                            }
            }

            if rec.work_order.is_subtask == False:
                if rec.work_order.subtask_exist:
                    history_list = list()
                    progress_history_ordered = self.env['progress.history'].search(
                        [('work_order', '=', rec.work_order.id)], order='date_create desc')
                    for progress in progress_history_ordered:
                        history_list.append(progress)

                    if rec.id != history_list[0].id:
                        raise ValidationError(_("You can only delete the latest progress."))
                    # subtasks = self.env['project.task'].search([('parent_task', '=', rec.work_order.id)])

                    # for sub in subtasks:
                    #     if sub.name == rec.subtask.name:
                    #         self._validate_delete_progress_subtask(sub, rec)

                    return action

                else:
                    history_list = list()

                    for progress in rec.work_order.progress_history_ids:
                        history_list.append(progress)

                    if rec.id != history_list[0].id:
                        raise ValidationError(_("You can only delete the latest progress."))

                    return action

            elif rec.work_order.is_subtask:
                history_list = list()
                parent = rec.work_order

                while parent.parent_task:
                    parent = parent.parent_task

                for progress in parent.progress_history_ids:
                    history_list.append(progress)

                if rec.progress_start_date_new != history_list[0].progress_start_date_new \
                        and rec.progress_end_date_new != history_list[0].progress_end_date_new \
                        and rec.progress_summary != history_list[0].progress_summary:
                    raise ValidationError(_("You can only delete the latest progress."))

                return action

    def _validate_delete_progress_subtask(self, subtask, rec):

        if len(rec) > 0:
            history_list = list()

            for progress in self.env['progress.history'].search([('work_order', '=', subtask.id)]):
                history_list.append(progress)

            if rec.progress_start_date_new != history_list[0].progress_start_date_new and rec.progress_end_date_new != \
                    history_list[0].progress_end_date_new and rec.progress_summary != history_list[0].progress_summary:
                raise ValidationError(_("You can only delete the latest progress."))

        return True

    project_id_progress = fields.Many2one('project.project', string="Project")
    stage_new_progress = fields.Many2one('project.stage.const', string="Stage")
    completion_ref_progress = fields.Many2one('project.completion.const', string="Contract")
    stage_computed_new_progress = fields.Many2many('project.stage.const', 'stage_progress_rel', string='Stages')
    sale_order_progress = fields.Many2one('sale.order.const', string="Contract")
    job_estimate = fields.Many2one(related="work_order.job_estimate", string="BOQ")
    name_progress = fields.Char(string='Work Order')
    attachment_file = fields.Many2many('attachment.file', 'progress', string="Attachments")
    project_internal = fields.Boolean(string='Project Internal')
    department_type = fields.Selection(related='project_id.department_type')

    #Approving Matrix
    approving_matrix_sale_id = fields.Many2one('approval.matrix.progress.history', string="Approval Matrix",
                                               store=True)
    approved_matrix_ids = fields.One2many('approval.matrix.progress.history.line', 'progress_id', store=True,
                                          string="Approved Matrix")
    is_progress_history_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                         compute='_compute_is_customer_approval_matrix')
    is_approval_matrix_filled = fields.Boolean(string="Custome Matrix", store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.progress.history.line',
                                              string='Progress Approval Matrix Line',
                                              store=False)

    approving_matrix_progress_id = fields.Many2one('approval.matrix.progress.history', string="Approval Matrix",
                                                   compute='_compute_approving_customer_matrix', store=True)
    progress_history_user_ids = fields.One2many('progress.history.approver.user', 'progress_history_approver_id',
                                                string='Approver')
    approvers_ids = fields.Many2many('res.users', 'progress_history_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    employee_id = fields.Many2one('res.users', string='Users')
    last_approved = fields.Many2one('res.users', string='Users')

    def _compute_is_job_order_complete(self):
        for record in self:
            record.is_job_order_complete = False
            if record.is_subtask:
                if record.work_order.parent_task.state == 'complete' or record.work_order.state == 'complete':
                    record.is_job_order_complete = True
            else:
                if record.work_order.state == 'complete':
                    record.is_job_order_complete = True

    @api.depends('project_id')
    def _compute_is_customer_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_progress_history_approval_matrix = IrConfigParam.get_param('is_progress_history_approval_matrix')
        for record in self:
            record.is_progress_history_approval_matrix = is_progress_history_approval_matrix

    @api.depends('project_id', 'branch_id', 'company_id', 'department_type')
    def _compute_approving_customer_matrix(self):
        for record in self:
            record.approving_matrix_progress_id = False
            if record.is_progress_history_approval_matrix:
                if record.department_type == 'project':
                    approving_matrix_progress_id = self.env['approval.matrix.progress.history'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('project_id', 'in', (record.project_id.id)),
                        ('department_type', '=', 'project'),
                        ('set_default', '=', False)], limit=1)

                    approving_matrix_default = self.env['approval.matrix.progress.history'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('set_default', '=', True),
                        ('department_type', '=', 'project')], limit=1)

                else:
                    approving_matrix_progress_id = self.env['approval.matrix.progress.history'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('project_id', 'in', (record.project_id.id)),
                        ('department_type', '=', 'department'),
                        ('set_default', '=', False)], limit=1)

                    approving_matrix_default = self.env['approval.matrix.progress.history'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('set_default', '=', True),
                        ('department_type', '=', 'department')], limit=1)

                if approving_matrix_progress_id:
                    record.approving_matrix_progress_id = approving_matrix_progress_id and approving_matrix_progress_id.id or False
                else:
                    if approving_matrix_default:
                        record.approving_matrix_progress_id = approving_matrix_default and approving_matrix_default.id or False

    @api.onchange('project_id', 'approving_matrix_progress_id')
    def onchange_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.project_id:
                app_list = []
                if record.is_progress_history_approval_matrix:
                    record.progress_history_user_ids = []
                    for rec in record.approving_matrix_progress_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'name': 1,
                                'user_ids': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                    record.approvers_ids = app_list
                    record.progress_history_user_ids = data

    def _compute_is_approver(self):
        for record in self:
            if record.approvers_ids:
                current_user = record.env.user
                matrix_line = sorted(record.progress_history_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(record.progress_history_user_ids)
                if app < a:
                    for line in record.progress_history_user_ids[app]:
                        if current_user in line.user_ids:
                            record.is_approver = True
                        else:
                            record.is_approver = False
                else:
                    record.is_approver = False
            else:
                record.is_approver = False

    def update_labour_value_on_approval(self):
        for record in self:
            if record.custom_project_progress == 'manual_estimation':
                for labour in record.labour_usage_ids:
                    if record.work_order.is_subtask:
                        parent_task = record._get_subtask_parents()
                    else:
                        parent_task = record.work_order

                    if parent_task:
                        labour.labour_usage_line_id.write({
                            'time': labour.time,
                        })
                        subtasks = parent_task._get_subtask(depth=0)
                        # update all subtask usage
                        for subtask in subtasks:
                            labour_usage_line_id = subtask.labour_usage_ids.filtered(lambda
                                                                                         x: x.project_scope_id.id == labour.project_scope_id.id and x.section_id.id == labour.section_id.id and x.group_of_product_id.id == labour.group_of_product_id.id and x.product_id.id == labour.product_id.id)
                            if labour_usage_line_id:
                                labour_usage_line_id.write({
                                    'time': labour.time,
                                })
                        # update parent usage
                        labour_usage_line_id = parent_task.labour_usage_ids.filtered(lambda
                                                                                         x: x.project_scope_id.id == labour.project_scope_id.id and x.section_id.id == labour.section_id.id and x.group_of_product_id.id == labour.group_of_product_id.id and x.product_id.id == labour.product_id.id)
                        if labour_usage_line_id:
                            labour_usage_line_id.write({
                                'time': labour.time,
                            })

                    cost_sheet = False
                    budget = False

                    actual_used_time = labour.time_usage
                    actual_used_amount = labour.time_usage * labour.contractors * labour.unit_price

                    if labour.labour_usage_line_id.bd_labour_id:
                        labour.labour_usage_line_id.bd_labour_id.reserved_time -= actual_used_time
                        labour.labour_usage_line_id.bd_labour_id.amt_res -= actual_used_amount
                        labour.labour_usage_line_id.bd_labour_id.amt_used += actual_used_amount
                        labour.labour_usage_line_id.bd_labour_id.time_used += actual_used_time

                        if not budget:
                            budget = labour.labour_usage_line_id.bd_labour_id.budget_id
                    if labour.labour_usage_line_id.cs_labour_id:
                        labour.labour_usage_line_id.cs_labour_id.reserved_time -= actual_used_time
                        labour.labour_usage_line_id.cs_labour_id.reserved_amt -= actual_used_amount
                        labour.labour_usage_line_id.cs_labour_id.actual_used_amt += actual_used_amount
                        labour.labour_usage_line_id.cs_labour_id.actual_used_time += actual_used_time

                        if not cost_sheet:
                            cost_sheet = labour.labour_usage_line_id.cs_labour_id.job_sheet_id

                    if cost_sheet:
                        if cost_sheet.budgeting_method == 'gop_budget':
                            cost_sheet.get_gop_labour_table()
                    if budget:
                        if cost_sheet.budgeting_method == 'gop_budget':
                            budget.get_gop_labour_table()

    def action_request_for_approving_matrix(self):
        for record in self:
            action_id = self.env.ref('equip3_construction_operation.progress_history_action_approval')
            template_id = self.env.ref(
                'equip3_construction_operation.email_template_reminder_for_progress_approval_original')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=progress.history'
            if record.progress_history_user_ids and len(record.progress_history_user_ids[0].user_ids) > 1:
                for approved_matrix_id in record.progress_history_user_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from': self.env.user.company_id.email,
                        'email_to': approver.partner_id.email,
                        'approver_name': approver.name,
                        'date': date.today(),
                        'url': url,
                        'work_order': self.work_order.name,
                    }
                    template_id.with_context(ctx).send_mail(record.id, force_send=True)
            else:
                approver = record.progress_history_user_ids[0].user_ids[0]
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': approver.partner_id.email,
                    'approver_name': approver.name,
                    'date': date.today(),
                    'url': url,
                    'work_order': self.work_order.name,
                }
                template_id.with_context(ctx).send_mail(record.id, force_send=True)

            record.write({'employee_id': self.env.user.id})

            for line in record.progress_history_user_ids:
                line.write({'approver_state': 'draft'})

    def action_confirm_approving_matrix(self):
        sequence_matrix = [data.name for data in self.progress_history_user_ids]
        sequence_approval = [data.name for data in self.progress_history_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.progress_history_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        for record in self:
            if record.project_id.custom_project_progress == 'manual_estimation':
                action_id = self.env.ref('equip3_construction_operation.action_view_task_inherited')
                action_id_2 = self.env.ref('equip3_construction_operation.progress_history_action_approval')
                template_app = self.env.ref('equip3_construction_operation.email_template_progress_history_approved')
                template_app_2 = self.env.ref(
                    'equip3_construction_operation.email_template_progress_history_approved_original')
                template_id = self.env.ref(
                    'equip3_construction_operation.email_template_reminder_for_progress_approval_temp')
                template_id_2 = self.env.ref(
                    'equip3_construction_operation.email_template_reminder_for_progress_approval_temp_original')
                user = self.env.user
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(record.work_order.id) + '&action=' + str(
                    action_id.id) + '&view_type=form&model=project.task'
                url_2 = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                    action_id_2.id) + '&view_type=form&model=progress.history'

                current_user = self.env.uid
                now = datetime.now(timezone(self.env.user.tz))
                dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"

                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for line in record.progress_history_user_ids:
                            for user in line.user_ids:
                                if current_user == user.user_ids.id:
                                    line.timestamp = fields.Datetime.now()
                                    record.approved_user_ids = [(4, current_user)]
                                    var = len(line.approved_employee_ids) + 1
                                    if line.minimum_approver <= var:
                                        line.approver_state = 'approved'
                                        string_approval = []
                                        string_approval.append(line.approval_status)
                                        if line.approval_status:
                                            string_approval.append(f"{self.env.user.name}:Approved")
                                            line.approval_status = "\n".join(string_approval)
                                            string_timestammp = [line.approved_time]
                                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                            line.approved_time = "\n".join(string_timestammp)
                                        else:
                                            line.approval_status = f"{self.env.user.name}:Approved"
                                            line.approved_time = f"{self.env.user.name}:{dateformat}"
                                        line.is_approve = True
                                    else:
                                        line.approver_state = 'pending'
                                        string_approval = []
                                        string_approval.append(line.approval_status)
                                        if line.approval_status:
                                            string_approval.append(f"{self.env.user.name}:Approved")
                                            line.approval_status = "\n".join(string_approval)
                                            string_timestammp = [line.approved_time]
                                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                            line.approved_time = "\n".join(string_timestammp)
                                        else:
                                            line.approval_status = f"{self.env.user.name}:Approved"
                                            line.approved_time = f"{self.env.user.name}:{dateformat}"
                                    line.approved_employee_ids = [(4, current_user)]

                        matrix_line = sorted(record.progress_history_user_ids.filtered(lambda r: r.is_approve == False))
                        progress = self.env['progress.history'].search([('progress_wiz', '=', record.progress_wiz.id)])
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            ctx = {
                                'email_from': self.env.user.company_id.email,
                                'email_to': record.employee_id.email,
                                'date': date.today(),
                                'work_order': self.work_order.name,
                                'employee_id': self.employee_id.name,
                                'code': self.number,
                                'url': url,
                                'url_2': url_2,
                            }
                            record.write({'state': 'approved',
                                          'approved_progress': record.progress})
                            record.update_labour_value_on_approval()
                            for rec in progress:
                                rec.write({'state': 'approved',
                                           'approved_progress': rec.progress})
                                template_app.sudo().with_context(ctx).send_mail(rec.work_order.id, True)
                                template_app_2.sudo().with_context(ctx).send_mail(rec.id, True)

                        else:
                            record.last_approved = self.env.user.id
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            for approving_matrix_line_user in matrix_line[0].user_ids:
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': approving_matrix_line_user.partner_id.email,
                                    'approver_name': approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter': record.last_approved.name,
                                    'code': self.number,
                                    'work_order': self.work_order.name,
                                    'url': url,
                                    'url_2': url_2,
                                }
                                for rec in progress:
                                    template_id.sudo().with_context(ctx).send_mail(rec.work_order.id, True)
                                    template_id_2.sudo().with_context(ctx).send_mail(rec.id, True)

                        job_id = self.work_order.id
                        action = self.env.ref('equip3_construction_operation.job_order_action_form').read()[0]
                        action['res_id'] = job_id
                        return action

                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved!'
                    ))

    def action_reject_approval(self):
        for record in self:
            action_id = self.env.ref('equip3_construction_operation.action_view_task_inherited')
            action_id_2 = self.env.ref('equip3_construction_operation.progress_history_action_approval')
            template_rej = self.env.ref('equip3_construction_operation.email_template_progress_history_rejected')
            template_rej_2 = self.env.ref(
                'equip3_construction_operation.email_template_progress_history_rejected_original')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.work_order.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=project.task'
            url_2 = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id_2.id) + '&view_type=form&model=progress.history'
            for user in record.progress_history_user_ids:
                for check_user in user.user_ids:
                    now = datetime.now(timezone(self.env.user.tz))
                    dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
                    if self.env.uid == check_user.id:
                        user.timestamp = fields.Datetime.now()
                        user.approver_state = 'reject'
                        string_approval = []
                        string_approval.append(user.approval_status)
                        if user.approval_status:
                            string_approval.append(f"{self.env.user.name}:Rejected")
                            user.approval_status = "\n".join(string_approval)
                            string_timestammp = [user.approved_time]
                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                            user.approved_time = "\n".join(string_timestammp)
                        else:
                            user.approval_status = f"{self.env.user.name}:Rejected"
                            user.approved_time = f"{self.env.user.name}:{dateformat}"

            record.approved_user = self.env.user.name + ' ' + 'has been Rejected!'
            progress = self.env['progress.history'].search([('progress_wiz', '=', record.progress_wiz.id)])
            ctx = {
                'email_from': self.env.user.company_id.email,
                'email_to': record.employee_id.email,
                'date': date.today(),
                'work_order': self.work_order.name,
                'employee_id': self.employee_id.name,
                'code': self.number,
                'url': url,
                'url_2': url_2,
            }
            record.write({'state': 'rejected'})
            for rec in progress:
                rec.write({'state': 'rejected'})
                template_rej.sudo().with_context(ctx).send_mail(rec.work_order.id, True)
                template_rej_2.sudo().with_context(ctx).send_mail(rec.id, True)

    def action_reject_approving_matrix(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'approval.matrix.progress.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            "context": {'default_job_id': self.work_order.id,
                        'is_reject_from_tree': False
                        }
        }

    # @api.depends('approving_matrix_sale_id')
    # def _compute_approval_matrix_filled(self):
    #     for record in self:
    #         record.is_approval_matrix_filled = False
    #         if record.approving_matrix_sale_id:
    #             record.is_approval_matrix_filled = True

    # def _get_approve_button(self):
    #     for record in self:
    #         matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved),
    #                              key=lambda r: r.sequence)
    #         if len(matrix_line) == 0:
    #             record.is_approve_button = False
    #             record.approval_matrix_line_id = False
    #         elif len(matrix_line) > 0:
    #             matrix_line_id = matrix_line[0]
    #             if self.env.user.id in matrix_line_id.user_name_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
    #                 record.is_approve_button = True
    #                 record.approval_matrix_line_id = matrix_line_id.id
    #             else:
    #                 record.is_approve_button = False
    #                 record.approval_matrix_line_id = False
    #         else:
    #             record.is_approve_button = False
    #             record.approval_matrix_line_id = False

    # @api.onchange('project_id')
    # def _onchange_project_new(self):
    #     self._compute_is_customer_approval_matrix()
    #     self._compute_approval_matrix_filled()

    # @api.onchange('sale_order')
    # def _onchange_sale_new(self):
    #     self._compute_is_customer_approval_matrix()
    #     self._compute_approval_matrix_filled()

    # @api.onchange('purchase_subcon')
    # def _onchange_purchase_new(self):
    #     self._compute_is_customer_approval_matrix()
    #     self._compute_approval_matrix_filled()

    # @api.onchange('job_estimate')
    # def _onchange_job_estimate_new(self):
    #     self._compute_is_customer_approval_matrix()
    #     self._compute_approval_matrix_filled()

    # @api.depends('approving_matrix_sale_id')
    # def _compute_approving_matrix_lines(self):
    #     for record in self:
    #         data = [(5, 0, 0)]
    #         if record.state == 'to_approve' and record.is_progress_history_approval_matrix:
    #             record.approved_matrix_ids = []
    #             counter = 1
    #             record.approved_matrix_ids = []
    #             for rec in record.approving_matrix_sale_id:
    #                 for line in rec.approver_matrix_line_ids:
    #                     data.append((0, 0, {
    #                         'sequence': counter,
    #                         'user_name_ids': [(6, 0, line.user_name_ids.ids)],
    #                         'minimum_approver': line.minimum_approver,
    #                     }))
    #                     counter += 1
    #             record.approved_matrix_ids = data

    # def action_confirm_approving(self):
    #     for record in self:
    #         progress = self.env['progress.history'].search([('progress_wiz', '=', record.progress_wiz.id)])
    #         record.write({'state': 'approved',
    #                       'approved_progress' : record.progress})
    #         for rec in progress:
    #             rec.write({'state': 'approved',
    #                       'approved_progress' : rec.progress})              
    #         job_id = self.work_order.id
    #         action = self.env.ref('equip3_construction_operation.job_order_action_form').read()[0]
    #         action['res_id'] = job_id
    #         return action

    # def action_confirm_approving_matrix(self):
    #     for record in self:
    #         action_id = self.env.ref('equip3_construction_operation.action_view_task_inherited')
    #         template_id = self.env.ref('equip3_construction_operation.email_template_reminder_for_progress_approval_temp')
    #         user = self.env.user
    #         base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #         url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=project.task'
    #         if record.is_approve_button and record.approval_matrix_line_id:
    #             approval_matrix_line_id = record.approval_matrix_line_id
    #             if user.id in approval_matrix_line_id.user_name_ids.ids and \
    #                 user.id not in approval_matrix_line_id.approved_users.ids:
    #                 name = approval_matrix_line_id.state_char or ''
    #                 if name != '':
    #                     name += "\n • %s: Approved" % (self.env.user.name)
    #                 else:
    #                     name += "• %s: Approved" % (self.env.user.name)

    #                 approval_matrix_line_id.write({
    #                     'last_approved': self.env.user.id, 'state_char': name,
    #                     'approved_users': [(4, user.id)]})
    #                 if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
    #                     approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True})
    #                     approver_name = ' and '.join(approval_matrix_line_id.mapped('user_name_ids.name'))
    #                     next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
    #                     if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_name_ids) > 1:
    #                         for approving_matrix_line_user in next_approval_matrix_line_id[0].user_name_ids:
    #                             ctx = {
    #                                 'email_from' : self.env.user.company_id.email,
    #                                 'email_to' : approving_matrix_line_user.partner_id.email,
    #                                 'approver_name' : approving_matrix_line_user.name,
    #                                 'date': date.today(),
    #                                 'submitter' : approver_name,
    #                                 'url' : url,
    #                             }
    #                             template_id.sudo().with_context(ctx).send_mail(record.work_order.id, True)
    #                     else:
    #                         if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_name_ids:
    #                             ctx = {
    #                                 'email_from' : self.env.user.company_id.email,
    #                                 'email_to' : next_approval_matrix_line_id[0].user_name_ids[0].partner_id.email,
    #                                 'approver_name' : next_approval_matrix_line_id[0].user_name_ids[0].name,
    #                                 'date': date.today(),
    #                                 'submitter' : approver_name,
    #                                 'url' : url,
    #                             }
    #                             template_id.sudo().with_context(ctx).send_mail(record.work_order.id, True)

    #         progress = self.env['progress.history'].search([('progress_wiz', '=', record.progress_wiz.id)])
    #         if progress:
    #             for res in progress:
    #                 if res.is_approve_button and res.approval_matrix_line_id:
    #                     approval_matrix_line_id = res.approval_matrix_line_id
    #                     if user.id in approval_matrix_line_id.user_name_ids.ids and \
    #                         user.id not in approval_matrix_line_id.approved_users.ids:
    #                         name = approval_matrix_line_id.state_char or ''
    #                         if name != '':
    #                             name += "\n • %s: Approved" % (self.env.user.name)
    #                         else:
    #                             name += "• %s: Approved" % (self.env.user.name)

    #                         approval_matrix_line_id.write({
    #                             'last_approved': self.env.user.id, 'state_char': name,
    #                             'approved_users': [(4, user.id)]})
    #                         if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
    #                             approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True})
    #                             approver_name = ' and '.join(approval_matrix_line_id.mapped('user_name_ids.name'))
    #                             next_approval_matrix_line_id = sorted(res.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
    #                             if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_name_ids) > 1:
    #                                 for approving_matrix_line_user in next_approval_matrix_line_id[0].user_name_ids:
    #                                     ctx = {
    #                                         'email_from' : self.env.user.company_id.email,
    #                                         'email_to' : approving_matrix_line_user.partner_id.email,
    #                                         'approver_name' : approving_matrix_line_user.name,
    #                                         'date': date.today(),
    #                                         'submitter' : approver_name,
    #                                         'url' : url,
    #                                     }
    #                                     template_id.sudo().with_context(ctx).send_mail(res.work_order.id, True)
    #                             else:
    #                                 if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_name_ids:
    #                                     ctx = {
    #                                         'email_from' : self.env.user.company_id.email,
    #                                         'email_to' : next_approval_matrix_line_id[0].user_name_ids[0].partner_id.email,
    #                                         'approver_name' : next_approval_matrix_line_id[0].user_name_ids[0].name,
    #                                         'date': date.today(),
    #                                         'submitter' : approver_name,
    #                                         'url' : url,
    #                                     }
    #                                     template_id.sudo().with_context(ctx).send_mail(res.work_order.id, True)

    #         if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
    #             record.write({'state': 'approved',
    #                           'approved_progress' : record.progress})

    #         if len(progress.approved_matrix_ids) == len(progress.approved_matrix_ids.filtered(lambda r: r.approved)):
    #             for rec in progress:
    #                 rec.write({'state': 'approved',
    #                         'approved_progress' : rec.progress})              

    #         job_id = self.work_order.id
    #         action = self.env.ref('equip3_construction_operation.job_order_action_form').read()[0]
    #         action['res_id'] = job_id
    #         return action

    @api.depends('subtask')
    def _get_subtask_parents(self):
        for rec in self:
            parent = rec.subtask.parent_task
            subtask_parents = []

            if not rec.work_order.subtask_exist:
                rec.subtask_parents = False
                return parent

            while parent:
                if parent == rec.work_order:
                    subtask = self.env['progress.history'].search([('work_order', '=', rec.subtask.id),
                                                                   ('progress_start_date_new', '=',
                                                                    rec.progress_start_date_new),
                                                                   ('progress_end_date_new', '=',
                                                                    rec.progress_end_date_new),
                                                                   ('progress_summary', '=', rec.progress_summary),
                                                                   ], limit=1)
                    if subtask.work_order.parent_task == rec.work_order:
                        subtask_exist = subtask.work_order.subtask_exist
                        if not subtask_exist:
                            rec.subtask_parents = False
                            return parent
                    break
                subtask_parents.append(parent.name)
                parent = parent.parent_task

            rec.subtask_parents = ' -> '.join(subtask_parents[::-1])
            return parent

    @api.depends('subtask_parents')
    def _get_hide_subtask_parents(self):
        for rec in self:
            if rec.subtask_parents:
                rec.hide_subtask_parents = False
            else:
                rec.hide_subtask_parents = True

    def action_progress_history_approve(self):
        self._compute_is_approver()

        approvable_progress = []
        non_approvable_progress = []

        dummy_project = None
        dummy_work_order = None

        for rec in self:
            if dummy_project == None and dummy_work_order == None:
                dummy_project = rec.project_id
                dummy_work_order = rec.work_order

            if rec.is_approve_button:
                if rec.state != 'rejected' and rec.state != 'approved':
                    approvable_progress.append(rec)
            elif rec.is_approve_button == False:
                if rec.state != 'rejected' and rec.state != 'approved':
                    non_approvable_progress.append(rec.id)

        if len(non_approvable_progress) > 0:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Progress History Non Approvable',
                'res_model': 'progress.history.approval.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_project_id': dummy_project.id,
                    'non_approvable_progress': non_approvable_progress,
                    'default_is_approve': True,
                    'default_work_order': dummy_work_order.id,
                }
            }
        elif len(approvable_progress) > 0 and len(non_approvable_progress) == 0:
            for rec in approvable_progress:
                rec.action_confirm_approving_matrix()

    def action_progress_history_reject(self):
        self._compute_is_approver()

        rejectable_progress = []
        non_rejectable_progress = []

        dummy_project = None
        dummy_work_order = None

        for rec in self:
            if dummy_project == None and dummy_work_order == None:
                dummy_project = rec.project_id
                dummy_work_order = rec.work_order

            if rec.is_approve_button:
                if rec.state != 'rejected' and rec.state != 'approved':
                    rejectable_progress.append(rec.id)
            elif rec.is_approve_button == False:
                if rec.state != 'rejected' and rec.state != 'approved':
                    non_rejectable_progress.append(rec.id)

        # if len(non_rejectable_progress) > 0 and len(rejectable_progress) > 0:
        #     return{
        #         'type': 'ir.actions.act_window',
        #         'name': 'Progress History Non Rejectable',
        #         'res_model': 'progress.history.approval.wizard',
        #         'view_type': 'form',
        #         'view_mode': 'form',
        #         'target': 'new',
        #         'context': {
        #             'default_project_id': dummy_project.id,
        #             'non_rejectable_progress': non_rejectable_progress,
        #             'rejectable_progress': rejectable_progress,
        #             'default_is_approve': False,
        #             'default_is_rejectable': True,
        #             'default_work_order': dummy_work_order.id,
        #         }
        #     }

        if len(rejectable_progress) > 0 and len(non_rejectable_progress) == 0:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Reject Reason',
                'res_model': 'approval.matrix.progress.reject',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                "context": {'default_job_id': dummy_work_order.id,
                            'rejectable_progress': rejectable_progress,
                            'is_reject_from_tree': True
                            }
            }

        elif len(non_rejectable_progress) > 0 and len(rejectable_progress) == 0:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Progress History Non Rejectable',
                'res_model': 'progress.history.approval.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_project_id': dummy_project.id,
                    'non_rejectable_progress': non_rejectable_progress,
                    'rejectable_progress': rejectable_progress,
                    'default_is_approve': False,
                    'default_is_rejectable': False,
                    'default_work_order': dummy_work_order.id,
                }
            }


class AttachmentsFile(models.Model):
    _name = 'attachment.file'
    _description = 'Attachment Tab'
    _order = 'sequence'

    progress = fields.Many2one('progress.history', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date")
    date_now = fields.Datetime(string="Date")
    attachment = fields.Binary(string='Attachment', widget='many2many_binary')
    name = fields.Char(string="File Name")
    file_size = fields.Integer(string='File Size')
    size = fields.Char("File Size")
    description = fields.Text(string="Description")

    @api.depends('progress.attachment_ids', 'progress.attachment_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.progress.attachment_ids:
                no += 1
                l.sr_no = no


class ProgressHistoryApproverUser(models.Model):
    _name = 'progress.history.approver.user'
    _description = 'Progress History Approver User'

    progress_history_approver_id = fields.Many2one('progress.history', string="Progress History")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'progress_history_app_emp_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('reject', 'Rejected')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'progress_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(related='progress_history_approver_id.state', string='Parent Status')

    @api.depends('progress_history_approver_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.progress_history_approver_id.progress_history_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len(rec.user_ids) < rec.minimum_approver and rec.progress_history_approver_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.progress_history_approver_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids


class JobNotesInherit(models.Model):
    _inherit = 'job.notes'

    @api.model
    def _domain_user(self):
        return [('company_id', '=', self.env.company.id)]

    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')

    user_id = fields.Many2one('res.users', domain=_domain_user)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
            'abs_construction_management.group_construction_manager'):
            domain.append('|')
            domain.append('&')
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))
            domain.append(('user_id', '=', self.env.user.id))
            domain.append('&')
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))
            domain.append(('create_uid', '=', self.env.user.id))
        elif self.env.user.has_group(
                'abs_construction_management.group_construction_manager') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))

        return super(JobNotesInherit, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
            'abs_construction_management.group_construction_manager'):
            domain.append('|')
            domain.append('&')
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))
            domain.append(('user_id', '=', self.env.user.id))
            domain.append('&')
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))
            domain.append(('create_uid', '=', self.env.user.id))
        elif self.env.user.has_group(
                'abs_construction_management.group_construction_manager') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))

        return super(JobNotesInherit, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                       orderby=orderby, lazy=lazy)

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if self.env.user.has_group(
                    'abs_construction_management.group_construction_user') and not self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_director'):
                if rec.department_type == 'project':
                    return {
                        'domain': {
                            'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id),
                                           ('id', 'in', self.env.user.project_ids.ids),
                                           ('branch_id', 'in', self.env.branches.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {
                            'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id),
                                           ('id', 'in', self.env.user.project_ids.ids),
                                           ('branch_id', 'in', self.env.branches.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {
                            'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id),
                                           ('branch_id', 'in', self.env.branches.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {
                            'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id),
                                           ('branch_id', 'in', self.env.branches.ids)]}
                    }
