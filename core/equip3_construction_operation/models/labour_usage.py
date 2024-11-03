from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import json


class LabourUsage(models.Model):
    _name = 'task.labour.usage'
    _description = 'Labour Usage'

    project_task_id = fields.Many2one('project.task', string='Work Order')
    cs_labour_id = fields.Many2one('material.labour', string='Cost Sheet Labour')
    bd_labour_id = fields.Many2one('budget.labour', string='Budget Labour')
    no = fields.Integer(string='No', compute="_sequence_ref")
    project_scope_id = fields.Many2one('project.scope.line', string="Project Scope ", required=True)
    section_id = fields.Many2one('section.line', string="Section", required=True)
    group_of_product_id = fields.Many2one('group.of.product', string="Group of Product ", required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    contractors = fields.Integer(string="Contractors")
    time = fields.Float(string="Time")
    time_left = fields.Float(string="Budgeted Time Left")
    uom_id = fields.Many2one('uom.uom', string="UOM")
    unit_price = fields.Float(string="Unit Price",related='cs_labour_id.price_unit', readonly=True)
    workers_ids = fields.Many2many('hr.employee', string="Workers")
    analytic_group_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    is_subtask = fields.Boolean(related='project_task_id.is_subtask')

    @api.depends('project_task_id')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.no = no
            for l in line.project_task_id.labour_usage_ids:
                no += 1
                l.no = no

    @api.onchange('time')
    def _onchange_time(self):
        for rec in self:
            if rec.time > rec.time_left:
                raise ValidationError(_('Assigned time cannot be more than the budgeted time'))

    @api.onchange('workers_ids')
    def _onchange_worker_ids (self):
        for rec in self:
            if len(rec.workers_ids) > rec.contractors:
                raise ValidationError(_('The number of workers cannot be more than the number of budgeted contractors'))


# Labour usage for progress history
class ProgressHistoryLabourUsage(models.Model):
    _name = 'progress.history.labour.usage'
    _description = 'Progress History Labour Usage'

    project_task_id = fields.Many2one('project.task', string='Work Order')
    labour_usage_line_id = fields.Many2one('task.labour.usage', string='Labour Usage Line')
    progress_history_id = fields.Many2one('progress.history', string='Progress History')
    cs_labour_id = fields.Many2one('material.labour', string='Cost Sheet Labour')
    bd_labour_id = fields.Many2one('budget.labour', string='Budget Labour')
    no = fields.Integer(string='No', compute="_sequence_ref")
    project_scope_id = fields.Many2one('project.scope.line', string="Project Scope ",)
    section_id = fields.Many2one('section.line', string="Section",)
    group_of_product_id = fields.Many2one('group.of.product', string="Group of Product ",)
    product_id = fields.Many2one('product.product', string="Product",)
    contractors = fields.Integer(string="Contractors", required=True)
    time_usage = fields.Float(string="Time Usage", default=0)
    time = fields.Float(string="Time", compute='_compute_time_left')
    temp_time_left = fields.Float(string="Time Left")
    time_left = fields.Float(string="Time Left")
    uom_id = fields.Many2one('uom.uom', string="UOM", )
    unit_price = fields.Float(string="Unit Price", readonly=True, default=0)
    workers_ids = fields.Many2many('hr.employee', string="Workers")
    analytic_group_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    custom_project_progress = fields.Selection(related='progress_history_id.project_id.custom_project_progress',
                                               string="Custom Project Progress")
    domain_worker = fields.Char(string='Worker', compute='_compute_domain_worker')
    is_add_progress = fields.Boolean(string="Is Add Progress", default=False)

    def _compute_time_left(self):
        for rec in self:
            if not rec.is_add_progress:
                if rec.custom_project_progress == 'manual_estimation':
                    rec.time = rec.temp_time_left - rec.time_usage
            else:
                rec.time = rec.temp_time_left

    @api.onchange('time_usage')
    def _onchange_time_usage(self):
        for rec in self:
            if rec.time_usage > rec.time:
                raise ValidationError(_('Time Usage cannot be more than the time'))

    @api.depends('project_task_id')
    def _compute_domain_worker(self):
        for rec in self:
            if rec.project_task_id:
                worker_ids = rec.project_task_id.labour_usage_ids.mapped('workers_ids')
                rec.domain_worker = json.dumps([('id', 'in', worker_ids.ids)])

    @api.depends('progress_history_id')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.no = no
            for l in line.progress_history_id.labour_usage_ids:
                no += 1
                l.no = no

    @api.onchange('workers_ids')
    def _onchange_worker_ids (self):
        for rec in self:
            if len(rec.workers_ids) > rec.contractors:
                raise ValidationError(_('The number of workers cannot be more than the number of budgeted contractors'))


# Labour usage for progress history wizard
class ProgressLabourUsage(models.Model):
    _name = 'progress.labour.usage'
    _description = 'Labour Usage'

    project_task_id = fields.Many2one('project.task', string='Work Order', default=lambda self: self.env.context.get('active_id'))
    labour_usage_line_id = fields.Many2one('task.labour.usage', string='Labour Usage Line')
    progress_history_id = fields.Many2one('progress.history.wiz', string='Progress History')
    cs_labour_id = fields.Many2one('material.labour', string='Cost Sheet Labour')
    bd_labour_id = fields.Many2one('budget.labour', string='Budget Labour')
    no = fields.Integer(string='No', compute="_sequence_ref")
    project_scope_id = fields.Many2one('project.scope.line', string="Project Scope ")
    section_id = fields.Many2one('section.line', string="Section")
    group_of_product_id = fields.Many2one('group.of.product', string="Group of Product ")
    product_id = fields.Many2one('product.product', string="Product")
    contractors = fields.Integer(string="Contractors", required=True, default=0)
    time_usage = fields.Float(string="Time Usage", default=0)
    time = fields.Float(string="Time", compute='_compute_time_left')
    temp_time_left = fields.Float(string="Time Left")
    time_left = fields.Float(string="Time Left")
    uom_id = fields.Many2one('uom.uom', string="UOM",)
    unit_price = fields.Float(string="Unit Price", readonly=True, default=0)
    workers_ids = fields.Many2many('hr.employee', string="Workers")
    analytic_group_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    custom_project_progress = fields.Selection(related='progress_history_id.project_id.custom_project_progress', string="Custom Project Progress")
    domain_worker = fields.Char(string='Worker', compute='_compute_domain_worker')
    is_add_progress = fields.Boolean(string="Is Add Progress", default=False)

    def _compute_time_left(self):
        for rec in self:
            if not rec.is_add_progress:
                if rec.custom_project_progress == 'manual_estimation':
                    rec.time = rec.temp_time_left - rec.time_usage
                    rec.temp_time_left = rec.time
            else:
                rec.time = rec.temp_time_left

    @api.onchange('time_usage')
    def _onchange_time_usage(self):
        for rec in self:
            if rec.time_usage > rec.time:
                raise ValidationError(_('Time Usage cannot be more than the time'))
            # if not rec.is_add_progress:
            #     if rec.custom_project_progress == 'manual_estimation':
            #         rec.time = rec.temp_time_left - rec.time_usage

    @api.depends('project_task_id')
    def _compute_domain_worker(self):
        for rec in self:
            if rec.project_task_id:
                worker_ids = rec.project_task_id.labour_usage_ids.mapped('workers_ids')
                rec.domain_worker = json.dumps([('id', 'in', worker_ids.ids)])

    @api.depends('progress_history_id')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.no = no
            for l in line.progress_history_id.labour_usage_ids:
                no += 1
                l.no = no

    @api.onchange('workers_ids')
    def _onchange_worker_ids (self):
        for rec in self:
            if len(rec.workers_ids) > rec.contractors:
                raise ValidationError(_('The number of workers cannot be more than the number of budgeted contractors'))

