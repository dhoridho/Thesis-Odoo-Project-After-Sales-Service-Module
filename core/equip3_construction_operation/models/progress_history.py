import base64
from odoo.tools import human_size
from odoo import api, fields, models, _
from datetime import datetime, date , timedelta
from odoo.exceptions import ValidationError
from lxml import etree
import json


class ProgressHistoryWiz(models.Model):
    _name = 'progress.history.wiz'
    _description = 'Create Progress History'

    @api.onchange('list_work_order', 'list_sale_order', 'list_job_estimate', 'list_project_id')
    def _onchange_get_work_order(self):
        for rec in self:
            if rec.is_create_from_list_view:
                rec.work_order = rec.list_work_order.id
                rec.sale_order = rec.list_sale_order.id
                rec.job_estimate = rec.list_job_estimate.id
                rec.project_id = rec.list_project_id.id
                rec.completion_ref = rec.list_completion_ref.id
                rec.stage_computed_new = [(6, 0, [v.id for v in rec.list_stage_computed_new])]
                rec.stage_new = rec.list_stage_new.id

                labour_usage = []
                for labour in rec.list_work_order.labour_usage_ids:
                    labour_usage.append((0, 0, {
                        'labour_usage_line_id': labour.id,
                        'project_task_id': labour.project_task_id.id,
                        'cs_labour_id': labour.cs_labour_id.id,
                        'bd_labour_id': labour.bd_labour_id.id,
                        'project_scope_id': labour.project_scope_id.id,
                        'section_id': labour.section_id.id,
                        'group_of_product_id': labour.group_of_product_id.id,
                        'product_id': labour.product_id.id,
                        'contractors': labour.contractors,
                        'temp_time_left': labour.time,
                        # 'time': labour.time,
                        'uom_id': labour.uom_id.id,
                        'unit_price': labour.unit_price,
                        'workers_ids': [(6, 0, [v.id for v in labour.workers_ids])],
                        'analytic_group_ids': [(6, 0, [v.id for v in labour.analytic_group_ids])],
                    }))
                rec.labour_usage_ids = [(5, 0, 0)]
                rec.labour_usage_ids = labour_usage

    @api.onchange('labour_usage_ids')
    def labour_usage_validation(self):
        for rec in self:
            for labour in rec.labour_usage_ids:
                if len(labour.labour_usage_line_id) == 0:
                    raise ValidationError(_("You're not allowed to create labour usage outside of declared labour usage in Job Order."))

    @api.model
    def create(self, vals):
        if vals.get('number', 'New') == 'New':
            vals['number'] = self.env['ir.sequence'].next_by_code('progress.history.sequence') or '/'
        res = super(ProgressHistoryWiz, self).create(vals)
        return res


    number = fields.Char(string='Number', copy=False, required=True, readonly=True,
                        index=True, default=lambda self: _('New'))
    work_order = fields.Many2one('project.task', string='Work Order')
    name = fields.Char(related="work_order.name", string='Work Order')
    project_id = fields.Many2one(related="work_order.project_id", string="Project")
    sale_order = fields.Many2one(related="work_order.sale_order", string="Contract")
    job_estimate = fields.Many2one (related="work_order.job_estimate", string="BOQ")
    purchase_subcon = fields.Many2one(related="work_order.purchase_subcon", string="Contract")
    completion_ref = fields.Many2one(related="work_order.completion_ref", string="Contract")
    date_create = fields.Datetime(default=fields.Datetime.now, copy=False, index=True, string="Creation date", readonly=True)
    create_by = fields.Many2one('res.users', index=True, readonly=True, default=lambda self: self.env.user, string="Created By")
    stage_computed_new = fields.Many2many('project.stage.const', string='Stages', compute='get_stages_new')
    stage_new = fields.Many2one(related="work_order.stage_new", string="Stage")
    progress_start_date_new = fields.Datetime(string='Progress Start Date')
    progress_end_date_new = fields.Datetime(string='Progress End Date')
    progress = fields.Float(string="Additional Progress (%)")
    progress_subtask = fields.Float(string="Additional Progress Subtask (%)")
    progress_summary = fields.Text(string='Progress Summary')
    attachment_ids= fields.One2many('attachment.file.wiz', 'progress')
    latest_completion = fields.Float(string="Latest Completion (%)")
    latest_completion_subtask = fields.Float(string="Latest Completion Subtask (%)")
    is_subcon = fields.Boolean(related="work_order.is_subcon")
    child_subtasks = fields.Many2many('project.task', string='Child Subtasks', compute='_get_child_subtasks')
    subtask = fields.Many2one('project.task', string='Subtask',domain="[('is_subtask', '=', True), ('project_id', '=', project_id), ('sale_order', '=', sale_order), ('stage_new', '=', stage_new), ('state', '=', 'inprogress'), ('id', 'in', child_subtasks)]")
    subtask_exist = fields.Boolean(related="work_order.subtask_exist")
    is_subtask = fields.Boolean(related="work_order.is_subtask")
    department_type = fields.Selection (related='project_id.department_type')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, readonly=True,
                                 default=lambda self: self.env.company)
    branch_id = fields.Many2one(related='project_id.branch_id', string="Branch")
    parent_task = fields.Many2one(related="work_order.parent_task", string="Parent Task")
    subtask_parents = fields.Text(string='Subtask Parent(s)', compute='_get_subtask_parents')
    hide_subtask_parents = fields.Boolean(string='Hide Subtask Parent(s)', default=True, compute='_get_hide_subtask_parents')
    state = fields.Selection([
                        ('draft', 'Draft'),
                        ('to_approve', 'Waiting For Approval'),
                        ('approved', 'Approved'),
                        ('rejected', 'Rejected')
                ], string="Request Status", default='draft')
    custom_project_progress = fields.Selection(related='project_id.custom_project_progress')

    is_progress_history_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                     compute='_compute_is_customer_approval_matrix')
    approving_matrix_sale_id = fields.Many2one('approval.matrix.progress.history', string="Approval Matrix",
                                               compute='_compute_approving_customer_matrix', store=True)
    approval_matrix_ids = fields.One2many('approval.matrix.progress.history.line', 'progress_id_wiz', store=True,
                                          string="Approved Matrix", compute='_compute_approving_matrix_lines')
    is_approval_matrix_filled = fields.Boolean(string="Custome Matrix", store=False)

    is_create_from_list_view = fields.Boolean(string="is_create_from_list_view", store=False)

    list_project_id = fields.Many2one("project.project", string="Project")
    list_sale_order = fields.Many2one('sale.order.const', string="Contract")
    list_job_estimate = fields.Many2one('job.estimate', string="BOQ")
    list_work_order = fields.Many2one('project.task', string="Work Order")
    list_stage_new = fields.Many2one('project.stage.const', string="Stage")
    list_completion_ref = fields.Many2one('project.completion.const', string="Completion Ref")
    list_stage_computed_new = fields.Many2many('project.stage.const', string='Stages', compute='list_get_stages_new')
    # custom_project_progress = fields.Selection(related='project_id.custom_project_progress', string='Custom Project Progress')
    labour_usage_ids = fields.One2many('progress.labour.usage', 'progress_history_id', string="Labour Usage")
    is_using_labour_attendance = fields.Boolean(related='project_id.is_using_labour_attendance')
    account_move_id = fields.Many2one('account.move', string="Account Move")

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if  self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
                if rec.department_type == 'project':
                    return {
                        'domain': {'list_project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids),('branch_id','in',self.env.branches.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'list_project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids),('branch_id','in',self.env.branches.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {'list_project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id),('branch_id','in',self.env.branches.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'list_project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id),('branch_id','in',self.env.branches.ids)]}
                    }

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ProgressHistoryWiz, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('abs_construction_management.group_construction_director'):
            root = etree.fromstring(res['arch'])
            res['arch'] = etree.tostring(root)
            if 'list_project_id' in res['fields']:
                res['fields']['list_project_id']['domain'] = [('id','in',self.env.user.project_ids.ids)]

        return res

    @api.depends('project_id')
    def _compute_is_customer_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_progress_history_approval_matrix = IrConfigParam.get_param('is_progress_history_approval_matrix')
        for record in self:
            record.is_progress_history_approval_matrix = is_progress_history_approval_matrix

    @api.depends('project_id','branch_id','company_id','department_type')
    def _compute_approving_customer_matrix(self):
        for record in self:
            record.approving_matrix_sale_id = False
            if record.is_progress_history_approval_matrix:
                if record.department_type == 'project':
                    approving_matrix_sale_id = self.env['approval.matrix.progress.history'].search([
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
                    approving_matrix_sale_id = self.env['approval.matrix.progress.history'].search([
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


                if approving_matrix_sale_id:
                    record.approving_matrix_sale_id = approving_matrix_sale_id and approving_matrix_sale_id.id or False
                else:
                    if approving_matrix_default:
                        record.approving_matrix_sale_id = approving_matrix_default and approving_matrix_default.id or False

    @api.depends('approving_matrix_sale_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.is_progress_history_approval_matrix:
                counter = 1
                record.approval_matrix_ids = []
                if record.approving_matrix_sale_id:
                    for rec in record.approving_matrix_sale_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'sequence': counter,
                                'approvers': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            counter += 1
                    record.approval_matrix_ids = data
                else:
                    record.approval_matrix_ids = False

    @api.depends('work_order')
    def _get_child_subtasks(self, subtask = False):
        # Get all subtasks on each layer(subtask on subtask and so on) using recursion
        for rec in self:
            if not subtask:
                child_subtasks = []
                if rec.work_order:
                    if rec.work_order.subtask_exist:
                        subtasks = self.env['project.task'].search([('is_subtask', '=', True),
                                                                    ('parent_task.name', '=', rec.work_order.name)])
                        for sub in subtasks:
                            if sub.subtask_exist:
                                child_subtasks += sub
                                rec.child_subtasks += sub
                            else:
                                rec.child_subtasks += sub
                        if len(child_subtasks) > 0:
                            self._get_child_subtasks(child_subtasks)
                    else:
                        rec.child_subtasks = False
                else:
                    rec.child_subtasks = False

            else:
                if subtask:
                    child_subtasks = []
                    for sub in subtask:
                        if sub.subtask_exist:
                            subtasks = self.env['project.task'].search(
                                [('is_subtask', '=', True), ('parent_task.name', '=', sub.name)])
                            for task in subtasks:
                                if task.subtask_exist:
                                    child_subtasks += task
                                    rec.child_subtasks += task
                                else:
                                    rec.child_subtasks += task
                            if len(child_subtasks) > 0:
                                self._get_child_subtasks(child_subtasks)
                        else:
                            rec.child_subtasks += sub
                else:
                    rec.child_subtasks = False


    @api.depends('subtask')
    def _get_subtask_parents(self):
        for rec in self:
            parent = rec.subtask.parent_task
            subtask_parents = []

            if not rec.work_order.subtask_exist:
                rec.subtask_parents = False
                return

            while parent:
                if parent == rec.work_order:
                    subtask = self.env['progress.history'].search([('work_order', '=', rec.subtask.id),
                                                                   ('progress_start_date_new', '=',rec.progress_start_date_new),
                                                                   ('progress_end_date_new', '=',rec.progress_end_date_new),
                                                                   ('progress_summary', '=', rec.progress_summary),
                                                                   ], limit=1)
                    if subtask.work_order.parent_task == rec.work_order:
                        subtask_exist = subtask.work_order.subtask_exist
                        if not subtask_exist:
                            rec.subtask_parents = False
                            return
                    break
                subtask_parents.append(parent.name)
                parent = parent.parent_task

            rec.subtask_parents = ' -> '.join(subtask_parents[::-1])


    @api.depends('subtask_parents')
    def _get_hide_subtask_parents(self):
        for rec in self:
            if rec.subtask_parents:
                rec.hide_subtask_parents = False
            else:
                rec.hide_subtask_parents = True

    @api.onchange('list_sale_order')
    def onchange_list_sale_order(self):
        self.list_completion_ref = False
        self.list_stage_new = False
        sale_stage = self.env['project.completion.const'].search([('completion_id', '=', self.list_project_id.id), ('name', '=', self.list_sale_order.id)], limit=1).id
        if self.list_sale_order:
            if sale_stage:
                self.write({'list_completion_ref': sale_stage})
            elif not sale_stage:
                warning_mess = {
                    'message': ('The work stage for contract "%s" has not yet been created. Please create contract completion stage first in the master project "%s" to continue creating this job order.'%((self.list_sale_order.name),(self.list_project_id.name))),
                    'title': "Warning"
                }
                if warning_mess != '':
                    return {'warning': warning_mess, 'value':{}}

    @api.onchange('job_estimate')
    def onchange_job_estimate(self):
        self.list_completion_ref = False
        self.list_stage_new = False
        sale_stage = self.env['project.completion.const'].search([('completion_id', '=', self.list_project_id.id), ('job_estimate', '=', self.list_job_estimate.id)], limit=1).id
        if self.list_job_estimate:
            if sale_stage:
                self.write({'list_completion_ref': sale_stage})
            elif not sale_stage:
                warning_mess = {
                    'message': ('The work stage for contract "%s" has not yet been created. Please create contract completion stage first in the master project "%s" to continue creating this job order.'%((self.job_estimate.name),(self.project_id.name))),
                    'title': "Warning"
                }
                if warning_mess != '':
                    return {'warning': warning_mess, 'value':{}}


    @api.depends('list_completion_ref')
    def list_get_stages_new(self):
        for rec in self:
            if rec.list_completion_ref and rec.list_completion_ref.stage_details_ids:
                rec.list_stage_computed_new = [(6, 0, rec.list_completion_ref.stage_details_ids.ids)]
            else:
                rec.list_stage_computed_new = [(6, 0, [])]

    @api.depends('completion_ref')
    def get_stages_new(self):
        for rec in self:
            if rec.completion_ref and rec.completion_ref.stage_details_ids:
                rec.stage_computed_new = [(6, 0, rec.completion_ref.stage_details_ids.ids)]
            else:
                rec.stage_computed_new = [(6, 0, [])]


    @api.onchange('subtask', 'progress_subtask')
    def compute_progress_subtask(self):
        for rec in self:
            # if rec.project_id.is_custom_project_progress == 'manual_estimation':
            if rec.subtask:
                progress = rec.progress_subtask
                weightage = rec.subtask.work_subtask_weightage
                task = rec.subtask
                parent_task_subtask = None
                while task:
                    if task.is_subtask:
                        progress = (progress * task.work_subtask_weightage) / 100
                        if task.parent_task and task != rec.work_order:
                            if task.parent_task == rec.work_order:
                                parent_task_subtask = task
                            task = task.parent_task
                        else:
                            break
                    else:
                        # progress = (progress * parent_task_subtask.work_subtask_weightage) / 100
                        break
                rec.update({'progress': progress})
            # elif rec.project_id.is_custom_project_progress == 'budget_estimation':
            #     raise ValidationError(_("Different calculation."))

                # else:
                #     # if rec.work_order.subtask_exist:
                #     progress = 0
                #     rec.update({'progress': progress})

    @api.onchange('subtask')
    def onchange_subtask_new(self):
        for rec in self:
            if rec.custom_project_progress == 'manual_estimation':
                rec.progress_subtask = 0
                rec.progress = 0

    @api.onchange('progress_start_date_new')
    def _check_start_date(self):
        for rec in self:
            if rec.work_order.subtask_exist:
                if rec.subtask:
                    if rec.progress_start_date_new:
                        if rec.subtask.actual_start_date:
                            if rec.subtask.actual_start_date > rec.progress_start_date_new:
                                raise ValidationError(_("Progress Start Date should be after subtask's Actual Start Date. Please re-set the Progress Start Date"))

            elif rec.work_order.subtask_exist == False:
                if rec.progress_start_date_new or rec.progress_end_date_new:
                    if rec.progress_start_date_new:
                        if rec.work_order.actual_start_date:
                            if rec.work_order.actual_start_date > rec.progress_start_date_new:
                                raise ValidationError(_("Progress Start Date should be after Actual Start Date. Please re-set the Progress Start Date"))

            if self.is_progress_history_approval_matrix == False:
                existing_historys = rec.work_order.progress_history_ids
                if len(existing_historys) >= 1:
                    for history in existing_historys:
                        if str(history.id) != str(rec.id):
                            if not rec.subtask:
                                if rec.progress_start_date_new:
                                    if history.progress_start_date_new <= rec.progress_start_date_new <= history.progress_end_date_new:
                                        raise ValidationError(_("This progress overlap with another progress."))
                            else:
                                if history.subtask.id == rec.subtask.id:
                                    if rec.progress_start_date_new:
                                        if history.progress_start_date_new <= rec.progress_start_date_new <= history.progress_end_date_new:
                                            raise ValidationError(_("This progress overlap with another progress with the same subtask."))

            else:
                existing_historys_approved = self.env['progress.history'].search([('work_order', '=', rec.work_order.id), ('state', '=', 'approved')])
                if len(existing_historys_approved) >= 1:
                    for history in existing_historys_approved:
                        if str(history.id) != str(rec.id):
                            if not rec.subtask:
                                if rec.progress_start_date_new:
                                    if history.progress_start_date_new <= rec.progress_start_date_new <= history.progress_end_date_new:
                                        raise ValidationError(_("This progress overlap with another progress."))
                            else:
                                if history.subtask.id == rec.subtask.id:
                                    if rec.progress_start_date_new:
                                        if history.progress_start_date_new <= rec.progress_start_date_new <= history.progress_end_date_new:
                                            raise ValidationError(_("This progress overlap with another progress with the same subtask."))

    @api.onchange('progress_start_date_new')
    def _check_start_date_list(self):
        for rec in self:
            if rec.list_work_order.subtask_exist:
                if rec.subtask:
                    if rec.progress_start_date_new:
                        if rec.subtask.actual_start_date:
                            if rec.subtask.actual_start_date > rec.progress_start_date_new:
                                raise ValidationError(_("Progress Start Date should be after subtask's Actual Start Date. Please re-set the Progress Start Date"))

            elif rec.list_work_order.subtask_exist == False:
                if rec.progress_start_date_new or rec.progress_end_date_new:
                    if rec.progress_start_date_new:
                        if rec.list_work_order.actual_start_date:
                            if rec.list_work_order.actual_start_date > rec.progress_start_date_new:
                                raise ValidationError(_("Progress Start Date should be after Actual Start Date. Please re-set the Progress Start Date"))

            if self.is_progress_history_approval_matrix == False:
                existing_historys = rec.list_work_order.progress_history_ids
                if len(existing_historys) >= 1:
                    for history in existing_historys:
                        if str(history.id) != str(rec.id):
                            if not rec.subtask:
                                if rec.progress_start_date_new:
                                    if history.progress_start_date_new <= rec.progress_start_date_new <= history.progress_end_date_new:
                                        raise ValidationError(_("This progress overlap with another progress."))
                            else:
                                if history.subtask.id == rec.subtask.id:
                                    if rec.progress_start_date_new:
                                        if history.progress_start_date_new <= rec.progress_start_date_new <= history.progress_end_date_new:
                                            raise ValidationError(_("This progress overlap with another progress with the same subtask."))

            else:
                existing_historys_approved = self.env['progress.history'].search([('work_order', '=', rec.list_work_order.id), ('state', '=', 'approved')])
                if len(existing_historys_approved) >= 1:
                    for history in existing_historys_approved:
                        if str(history.id) != str(rec.id):
                            if not rec.subtask:
                                if rec.progress_start_date_new:
                                    if history.progress_start_date_new <= rec.progress_start_date_new <= history.progress_end_date_new:
                                        raise ValidationError(_("This progress overlap with another progress."))
                            else:
                                if history.subtask.id == rec.subtask.id:
                                    if rec.progress_start_date_new:
                                        if history.progress_start_date_new <= rec.progress_start_date_new <= history.progress_end_date_new:
                                            raise ValidationError(_("This progress overlap with another progress with the same subtask."))


    @api.onchange('progress_end_date_new')
    def _check_end_date(self):
         for rec in self:
            if rec.progress_start_date_new or rec.progress_end_date_new:
                if rec.progress_start_date_new:
                    if rec.progress_start_date_new > rec.progress_end_date_new:
                        raise ValidationError(_("progress end date should be after progress start date "))

    @api.onchange('subtask')
    def _onchange_latest_completion_subtask(self):
        for rec in self:
            rec.latest_completion_subtask = 0
            if rec.subtask:
                total = 0
                for existing_history in rec.subtask.progress_history_ids:
                    if rec.is_progress_history_approval_matrix == False:
                        total += existing_history.progress
                    else:
                        if existing_history.state == 'approved':
                            total += existing_history.progress
                rec.latest_completion_subtask = total

    @api.onchange('work_order')
    def _onchange_latest_completion(self):
        total = 0
        for rec in self:
            rec.latest_completion = 0
            if rec.work_order:
                total = 0
                for existing_history in rec.work_order.progress_history_ids:
                    if rec.is_progress_history_approval_matrix == False:
                        if existing_history.work_order.id == rec.work_order.id:
                            total += existing_history.progress
                    else:
                        if existing_history.work_order.id == rec.work_order.id:
                            total += existing_history.approved_progress
                rec.latest_completion = total

        # for res in self:
        #     if res.is_progress_history_approval_matrix == False:
        #         existing_historys = self.env['progress.history'].search([('work_order','=', res.work_order.id)])
        #     else:
        #         existing_historys = self.env['progress.history'].search([('work_order','=', res.work_order.id), ('state','=', 'approved')])

        #     for existing_history in existing_historys:
        #         total += existing_history.progress
        #         res.latest_completion = total
        # return total

    # @api.onchange('progress_subtask')
    # def onchange_progress_subtask(self):
    #     if self.latest_completion_subtask + self.progress_subtask > 100:
    #         raise ValidationError(_("Total Progress Completion of subtask is more than 100%.\nPlease, re-set the Additional Progress (%) Subtask of this progress"))

    @api.onchange('progress_subtask')
    def onchange_progress_subtask(self):
        weig_sub = 0
        max_weightage = 0
        current_progress = 0
        rest_task = 0
        if self.subtask:
            subtask_sub = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('parent_task', '=', self.subtask.id)])
            if subtask_sub:
                for sub in subtask_sub:
                    weig_sub += sub.work_subtask_weightage
                    max_weightage = 100 - weig_sub
            else:
                max_weightage = 100

            history = self.env['progress.history'].search([('project_id', '=', self.project_id.id), ('work_order', '=', self.subtask.id), ('subtask', '=', False), ('state', '=', 'approved')])
            if history:
                for his in history:
                    current_progress += his.progress
            else:
                current_progress = 0

            rest_task = max_weightage - current_progress

            if self.progress_subtask > rest_task:
                raise ValidationError(_("Total Progress Completion for this subtask cannot be more than '{}%'. The rest of the progress can be added on subtask of this selected subtask.\nPlease, re-set the Additional Progress (%) of this progress.".format(rest_task)))

    @api.constrains('progress_subtask')
    def constraint_progress_subtask(self):
        for rec in self:
            if rec.subtask:
                if rec.progress_subtask < 1:
                    raise ValidationError(_("Additional Progress Subtask on the added progress history must be more than 0%"))

    @api.onchange('progress')
    def onchange_progress(self):
        weig_sub = 0
        max_weightage = 0
        current_progress = 0
        rest_task = 0
        if self.subtask_exist == False:
            if self.custom_project_progress == 'manual_estimation':
                if self.latest_completion + self.progress > 100:
                    raise ValidationError(_("Total Progress Completion is more than 100%.\nPlease, re-set the Additional Progress (%) of this progress."))

        else:
            subtask = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('parent_task', '=', self.work_order.id)])
            if subtask:
                for sub in subtask:
                    weig_sub += sub.work_subtask_weightage
                    max_weightage = 100 - weig_sub
            else:
                max_weightage = 100

            history = self.env['progress.history'].search([('project_id', '=', self.project_id.id), ('work_order', '=', self.work_order.id), ('subtask', '=', False), ('state', '=', 'approved')])
            if history:
                for his in history:
                    current_progress += his.progress
            else:
                current_progress = 0

            rest_task = max_weightage - current_progress

            if not self.subtask:
                if self.progress > rest_task:
                    raise ValidationError(_("Total Progress Completion for this job order cannot be more than '{}%'. The rest of the progress can be added on subtask of this job order.\nPlease, re-set the Additional Progress (%) of this progress.".format(rest_task)))


    @api.constrains('progress')
    def onchange_progress_22(self):
        for rec in self:
            if rec.progress <= 0:
                raise ValidationError(_("Additional Progress on the added progress history must be more than 0%"))

    @api.onchange('is_subcon')
    def onchange_is_subcon(self):
        for res in self:
            if res.is_subcon == False:
                res.purchase_subcon = False

    # @api.depends('approving_matrix_sale_id')
    # def _compute_approval_matrix_filled(self):
    #     for record in self:
    #         record.is_approval_matrix_filled = False
    #         if record.approving_matrix_sale_id:
    #             record.is_approval_matrix_filled = True

    # @api.onchange('project_id','is_progress_history_approval_matrix')
    # def onchange_warning_approval(self):
    #     for rec in self:
    #         warning_mess = ''
    #         if rec.project_id:
    #             if rec.is_progress_history_approval_matrix == True:
    #                 if len(rec.approved_matrix_ids) == 0:
    #                     warning_mess = {
    #                             'message': ("There's no progress history approval matrix for this project. You have to create it first."),
    #                             'title': "Warning"
    #                     }

    #         if warning_mess != '':
    #             return {'warning': warning_mess, 'value':{}}            

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
    #     data = [(5, 0, 0)]
    #     for record in self:
    #         if record.is_progress_history_approval_matrix:
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

    def get_labour_usage_values(self, is_parent=False, subtask_parent=False, job_order=False):
        for rec in self:
            labour_usage = []

            for labour in rec.labour_usage_ids:
                labour.is_add_progress = True
                labour_usage.append((0, 0, {
                    'labour_usage_line_id': labour.labour_usage_line_id.id,
                    'project_task_id': labour.project_task_id.id,
                    'cs_labour_id': labour.cs_labour_id.id,
                    'bd_labour_id': labour.bd_labour_id.id,
                    'project_scope_id': labour.project_scope_id.id,
                    'section_id': labour.section_id.id,
                    'group_of_product_id': labour.group_of_product_id.id,
                    'product_id': labour.product_id.id,
                    'contractors': labour.contractors,
                    'temp_time_left': labour.temp_time_left,
                    'time_usage': labour.time_usage,
                    # 'time': labour.time,
                    # 'time_left': labour.time_left,
                    'uom_id': labour.uom_id.id,
                    'unit_price': labour.unit_price,
                    'workers_ids': [(6, 0, labour.workers_ids.ids)],
                    'analytic_group_ids': [(6, 0, labour.analytic_group_ids.ids)],
                    'is_add_progress': True,
                }))
                if not rec.is_progress_history_approval_matrix:
                    parent_task = False
                    if subtask_parent:
                        parent_task = subtask_parent
                    elif not job_order.is_subtask:
                        parent_task = job_order

                    if parent_task:
                        labour.labour_usage_line_id.write({
                            'time': labour.time,
                        })
                        subtasks = parent_task._get_subtask(depth=0)
                        # update all subtask usage
                        for subtask in subtasks:
                            labour_usage_line_id = subtask.labour_usage_ids.filtered(lambda x: x.project_scope_id.id == labour.project_scope_id.id and x.section_id.id == labour.section_id.id and x.group_of_product_id.id == labour.group_of_product_id.id and x.product_id.id == labour.product_id.id)
                            if labour_usage_line_id:
                                labour_usage_line_id.write({
                                    'time': labour.time,
                                })
                        # update parent usage
                        labour_usage_line_id = parent_task.labour_usage_ids.filtered(lambda x: x.project_scope_id.id == labour.project_scope_id.id and x.section_id.id == labour.section_id.id and x.group_of_product_id.id == labour.group_of_product_id.id and x.product_id.id == labour.product_id.id)
                        if labour_usage_line_id:
                            labour_usage_line_id.write({
                                'time': labour.time,
                            })
                    # else:
                    #     if not is_parent:
                    #         labour.labour_usage_line_id.write({
                    #             'time': labour.time,
                    #         })
                    #     else:
                    #         labour_usage_line_id = subtask_parent.labour_usage_ids.filtered(lambda x: x.project_scope_id.id == labour.project_scope_id.id and x.section_id.id == labour.section_id.id and x.group_of_product_id.id == labour.group_of_product_id.id and x.product_id.id == labour.product_id.id)
                    #         if labour_usage_line_id:
                    #             labour_usage_line_id.write({
                    #                 'time': labour.time,
                    #             })
            return labour_usage

    def _prepare_vals_self_task(self, res, job_order, attachment_line, progress = False, to_bottom = False):
        if res.is_progress_history_approval_matrix == False:
            state = 'approved'
            approved_progress = progress or res.progress
        else:
            state = 'to_approve'
            approved_progress = 0

        latest_completion = 0
        if to_bottom:
            latest_completion = res.latest_completion_subtask
        else:
            latest_completion = res.latest_completion

        return {
                'project_id': res.project_id.id,
                'sale_order': res.sale_order.id,
                'job_estimate': res.job_estimate.id,
                'purchase_subcon': res.purchase_subcon.id,
                'completion_ref': res.completion_ref.id,
                'stage_new': res.stage_new.id,
                'stage_computed_new': [(6, 0, [v.id for v in res.stage_computed_new])],
                'work_order': job_order.id,
                'name': job_order.name,
                'subtask': False,
                'progress_start_date_new': res.progress_start_date_new,
                'progress_end_date_new': res.progress_end_date_new,
                'latest_completion': latest_completion or res.latest_completion,
                'latest_completion_subtask': 0,
                'current_total_duration': res.current_total_duration or 0,
                'progress_subtask': 0,
                'progress': progress or res.progress,
                'approved_progress': approved_progress,
                'progress_summary': res.progress_summary,
                'create_by': res.create_by.id,
                'date_create': datetime.now(),
                'is_progress_history_approval_matrix': res.is_progress_history_approval_matrix,
                'attachment_ids': attachment_line,
                'progress_wiz': res.id,
                'state': state,
                'number': self.number,
                'labour_usage_ids': self.get_labour_usage_values(job_order=job_order),
            }

    def _prepare_vals_self_have_subtask(self, res, job_order, attachment_line):
        if res.is_progress_history_approval_matrix == False:
            state = 'approved'
            approved_progress = res.progress
        else:
            state = 'to_approve'
            approved_progress = 0
        return {
                'project_id': res.project_id.id,
                'sale_order': res.sale_order.id,
                'job_estimate': res.job_estimate.id,
                'purchase_subcon': res.purchase_subcon.id,
                'completion_ref': res.completion_ref.id,
                'stage_new': res.stage_new.id,
                'stage_computed_new': [(6, 0, [v.id for v in res.stage_computed_new])],
                'work_order': job_order.id,
                'name': job_order.name,
                'subtask': res.subtask.id,
                'progress_start_date_new': res.progress_start_date_new,
                'progress_end_date_new': res.progress_end_date_new,
                'latest_completion': res.latest_completion,
                'latest_completion_subtask': res.latest_completion_subtask,
                'progress_subtask': res.progress_subtask,
                'progress': res.progress,
                'approved_progress': approved_progress,
                'progress_summary': res.progress_summary,
                'create_by': res.create_by.id,
                'date_create': datetime.now(),
                'is_progress_history_approval_matrix': res.is_progress_history_approval_matrix,
                'attachment_ids': attachment_line,
                'progress_wiz': res.id,
                'state': state,
                'number': self.number,
            }

    def _prepare_vals_subtask_from_parent(self, res, attachment_line):
        if res.is_progress_history_approval_matrix == False:
            state = 'approved'
            approved_progress = res.progress_subtask
        else:
            state = 'to_approve'
            approved_progress = 0
        return {
                'project_id': res.project_id.id,
                'sale_order': res.sale_order.id,
                'job_estimate': res.job_estimate.id,
                'purchase_subcon': res.purchase_subcon.id,
                'completion_ref': res.completion_ref.id,
                'stage_new': res.stage_new.id,
                'stage_computed_new': [(6, 0, [v.id for v in res.stage_computed_new])],
                'work_order': res.subtask.id,
                'name': res.subtask.name,
                'subtask': False,
                'progress_start_date_new': res.progress_start_date_new,
                'progress_end_date_new': res.progress_end_date_new,
                'latest_completion': res.latest_completion_subtask,
                'latest_completion_subtask': 0,
                'progress_subtask': 0,
                'progress': res.progress_subtask,
                'approved_progress': approved_progress,
                'progress_summary': res.progress_summary,
                'create_by': res.create_by.id,
                'date_create': datetime.now(),
                'is_progress_history_approval_matrix': res.is_progress_history_approval_matrix,
                'attachment_ids': attachment_line,
                'progress_wiz': res.id,
                'state': state,
                'number': self.number,
            }

    def _prepare_vals_parent_from_subtask(self, res, job_order, attachment_line, progress = False, subtask = False):
        if res.is_progress_history_approval_matrix == False:
            state = 'approved'
            approved_progress = progress or (res.progress * job_order.work_subtask_weightage) / 100
        else:
            state = 'to_approve'
            approved_progress = 0
        return {
                'project_id': res.project_id.id,
                'sale_order': res.sale_order.id,
                'job_estimate': res.job_estimate.id,
                'purchase_subcon': res.purchase_subcon.id,
                'completion_ref': res.completion_ref.id,
                'stage_new': res.stage_new.id,
                'stage_computed_new': [(6, 0, [v.id for v in res.stage_computed_new])],
                'work_order': job_order.parent_task.id,
                'name': job_order.parent_task.name,
                'subtask': subtask.id or job_order.id,
                'progress_start_date_new': res.progress_start_date_new,
                'progress_end_date_new': res.progress_end_date_new,
                'latest_completion': job_order.parent_task.progress_task or 0,
                'latest_completion_subtask': res.latest_completion,
                'current_total_duration': res.current_total_duration or 0,
                'progress_subtask': subtask.progress_history_ids[0].progress,
                'progress': progress or (res.progress * job_order.work_subtask_weightage) / 100,
                'approved_progress': approved_progress,
                'progress_summary': res.progress_summary,
                'create_by': res.create_by.id,
                'date_create': datetime.now(),
                'is_progress_history_approval_matrix': res.is_progress_history_approval_matrix,
                'attachment_ids': attachment_line,
                'progress_wiz': res.id,
                'state': state,
                'number': self.number,
                'labour_usage_ids': self.get_labour_usage_values(is_parent=True, subtask_parent=job_order.parent_task, job_order=job_order),
            }

    def _parent_from_subtask(self):
        def _looping_vals_parent_from_subtask(res, job_order, attachment_line, job_parent=False):
            parent = self.env['progress.history'].sudo().create(self._prepare_vals_parent_from_subtask(res, job_order, attachment_line))
            job_parent = parent.work_order.id
            if job_parent.is_progress_history_approval_matrix == False:
                state = 'approved'
                approved_progress = (job_parent.progress * job_order.work_subtask_weightage) / 100
            else:
                state = 'to_approve'
                approved_progress = 0
            self.env['progress.history'].sudo().create({
                    'project_id': job_parent.project_id.id,
                    'sale_order': job_parent.sale_order.id,
                    'job_estimate': job_parent.job_estimate.id,
                    'purchase_subcon': job_parent.purchase_subcon.id,
                    'completion_ref': job_parent.completion_ref.id,
                    'stage_new': job_parent.stage_new.id,
                    'stage_computed_new': [(6, 0, [v.id for v in job_parent.stage_computed_new])],
                    'work_order': job_order.parent_task.id,
                    'name': job_order.parent_task.name,
                    'subtask': job_order.id,
                    'progress_start_date_new': job_parent.progress_start_date_new,
                    'progress_end_date_new': job_parent.progress_end_date_new,
                    'latest_completion': job_parent.parent_task.progress_task,
                    'latest_completion_subtask': job_parent.latest_completion,
                    'progress_subtask': job_parent.progress,
                    'progress': (job_parent.progress * job_order.work_subtask_weightage) / 100,
                    'approved_progress': approved_progress,
                    'progress_summary': job_parent.progress_summary,
                    'create_by': job_parent.create_by.id,
                    'date_create': datetime.now(),
                    'is_progress_history_approval_matrix': job_parent.is_progress_history_approval_matrix,
                    'attachment_ids': attachment_line,
                    'progress_wiz': res.id,
                    'state': state,
                    'number': self.number,
                }
            )

            if parent.work_order.is_subtask == True:
                parent_job = parent.work_order
                self.env['progress.history'].sudo().create(self._prepare_vals_parent_from_subtask(res, attachment_line, job_order = parent_job))
                _looping_vals_parent_from_subtask()
            else:
                pass

    def add_progress(self):
        for res in self:
            if res.work_order:
                job_order = res.work_order
            else:
                job_order = self.env['project.task'].browse(self.env.context.get('active_id'))

            attachment_line = []
            for attach in res.attachment_ids:
                attachment_line.append(
                    (0, 0, {'date_now': res.progress_end_date_new,
                            'attachment': attach.attachment,
                            'name': attach.name,
                            'description': attach.description,
                            }
                    ))

            if res.custom_project_progress == 'manual_estimation':
                if res.is_progress_history_approval_matrix is False:
                    if job_order.is_subtask == False:
                        if job_order.subtask_exist == False:
                            progress_line = res.env['progress.history'].sudo().create(res._prepare_vals_self_task(res, job_order, attachment_line))
                        else:
                            if not res.subtask:
                                progress_line = res.env['progress.history'].sudo().create(
                                    res._prepare_vals_self_task(res, job_order, attachment_line))
                            else:
                                task = res.subtask
                                subtask = res.subtask
                                progress = res.progress_subtask or res.progress
                                i = 0
                                while task:
                                    if not task.subtask_exist:
                                        progress_line = res.env['progress.history'].sudo().create(
                                            res._prepare_vals_self_task(res, task, attachment_line,
                                                                        progress, True))  # Bottom subtask
                                        i += 1

                                        progress = (progress * task.work_subtask_weightage) / 100
                                        res.env['progress.history'].sudo().create(
                                            res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress,
                                                                                  subtask))  # Parent of bottom subtask
                                        if task.parent_task:
                                            task = task.parent_task
                                        else:
                                            break
                                    else:
                                        if task.is_subtask:
                                            if task.subtask_exist and res.subtask and i < 1:
                                                #selected subtask
                                                progress_line = res.env['progress.history'].sudo().create(
                                                    res._prepare_vals_self_task(res, task, attachment_line, progress, True))
                                                i += 1

                                            progress = (progress * task.work_subtask_weightage) / 100
                                            res.env['progress.history'].sudo().create(
                                                res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress,
                                                                                      subtask))
                                            if task.parent_task:
                                                task = task.parent_task
                                            else:
                                                break
                                        else:
                                            progress = (progress * task.work_subtask_weightage) / 100
                                            res.env['progress.history'].sudo().create(
                                                res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress,
                                                                                      subtask))
                                            break
                    else:
                        task = job_order
                        subtask = job_order
                        progress = res.progress_subtask or res.progress
                        i = 0
                        while task:
                            if not task.subtask_exist:
                                progress_line = res.env['progress.history'].sudo().create(
                                    res._prepare_vals_self_task(res, job_order, attachment_line, progress, True))#Bottom subtask
                                i+=1

                                progress = (progress * task.work_subtask_weightage) / 100
                                res.env['progress.history'].sudo().create(
                                    res._prepare_vals_parent_from_subtask(res, job_order, attachment_line, progress, subtask)) #Parent of bottom subtask
                                if task.parent_task:
                                    task = task.parent_task
                                else:
                                    break
                            else:
                                if task.is_subtask:
                                    if task.subtask_exist and not res.subtask and i <1:
                                        progress_line = res.env['progress.history'].sudo().create(
                                            res._prepare_vals_self_task(res, job_order, attachment_line,progress, True))
                                        i += 1

                                    progress = (progress * task.work_subtask_weightage) / 100
                                    res.env['progress.history'].sudo().create(res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress, subtask))
                                    if task.parent_task:
                                        task = task.parent_task
                                else:
                                    progress = (progress * task.work_subtask_weightage) / 100
                                    res.env['progress.history'].sudo().create(res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress, subtask))
                                    break
                    cost_sheet = False
                    budget = False

                    for usage in res.labour_usage_ids:
                        actual_used_time = usage.time_usage
                        actual_used_amount = usage.time_usage * usage.contractors * usage.unit_price

                        if usage.labour_usage_line_id.bd_labour_id:
                            usage.labour_usage_line_id.bd_labour_id.reserved_time -= actual_used_time
                            usage.labour_usage_line_id.bd_labour_id.amt_res -= actual_used_amount
                            usage.labour_usage_line_id.bd_labour_id.amt_used += actual_used_amount
                            usage.labour_usage_line_id.bd_labour_id.time_used += actual_used_time

                            if not budget:
                                budget = usage.labour_usage_line_id.bd_labour_id.budget_id
                        if usage.labour_usage_line_id.cs_labour_id:
                            usage.labour_usage_line_id.cs_labour_id.reserved_time -= actual_used_time
                            usage.labour_usage_line_id.cs_labour_id.reserved_amt -= actual_used_amount
                            usage.labour_usage_line_id.cs_labour_id.actual_used_amt += actual_used_amount
                            usage.labour_usage_line_id.cs_labour_id.actual_used_time += actual_used_time

                            if not cost_sheet:
                                cost_sheet = usage.labour_usage_line_id.cs_labour_id.job_sheet_id

                    if cost_sheet:
                        if cost_sheet.budgeting_method == 'gop_budget':
                            cost_sheet.get_gop_labour_table()
                    if budget:
                        if cost_sheet.budgeting_method == 'gop_budget':
                            budget.get_gop_labour_table()

                elif res.is_progress_history_approval_matrix is True:
                    if len(res.approval_matrix_ids) == 0:
                        raise ValidationError(
                            _("There's no progress history approval matrix for this project or approval matrix default created. You have to create it first."))

                    if job_order.is_subtask == False:
                        if job_order.subtask_exist == False:
                            progress_line = res.env['progress.history'].sudo().create(
                                res._prepare_vals_self_task(res, job_order, attachment_line))
                            self.set_approval_values(job_order, progress_line)
                            self.set_message(job_order, progress_line)
                        else:
                            if not res.subtask:
                                progress_line = res.env['progress.history'].sudo().create(
                                    res._prepare_vals_self_task(res, job_order, attachment_line))
                                self.set_approval_values(job_order, progress_line)
                                self.set_message(job_order, progress_line)
                            else:
                                task = res.subtask
                                subtask = res.subtask
                                progress = res.progress_subtask or res.progress
                                progress_line = None
                                i = 0
                                while task:
                                    if not task.subtask_exist:
                                        progress_line = res.env['progress.history'].sudo().create(
                                            res._prepare_vals_self_task(res, task, attachment_line,
                                                                        progress, True))  # Bottom subtask
                                        self.set_approval_values(task, progress_line)
                                        i += 1

                                        progress = (progress * task.work_subtask_weightage) / 100
                                        progress_line = res.env['progress.history'].sudo().create(
                                            res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress,
                                                                                  subtask))  # Parent of bottom subtask
                                        self.set_approval_values(task.parent_task, progress_line)
                                        self.set_message(task, progress_line)
                                        if task.parent_task:
                                            task = task.parent_task
                                        else:
                                            break
                                    else:
                                        if task.is_subtask:
                                            if task.subtask_exist and res.subtask and i < 1:
                                                # selected subtask
                                                progress_line = res.env['progress.history'].sudo().create(
                                                    res._prepare_vals_self_task(res, task, attachment_line, progress, True))
                                                self.set_approval_values(task, progress_line)
                                                self.set_message(task, progress_line)
                                                i += 1

                                            progress = (progress * task.work_subtask_weightage) / 100
                                            progress_line = res.env['progress.history'].sudo().create(
                                                res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress,
                                                                                      subtask))
                                            self.set_approval_values(task, progress_line)
                                            self.set_message(task, progress_line)
                                            if task.parent_task:
                                                task = task.parent_task
                                            else:
                                                break
                                        else:
                                            self.set_approval_values(task, progress_line)
                                            self.set_message(task, progress_line)
                                            break
                    else:
                        task = job_order
                        subtask = job_order
                        progress = res.progress_subtask or res.progress
                        progress_line = None
                        i = 0
                        while task:
                            if not task.subtask_exist:
                                progress_line = res.env['progress.history'].sudo().create(
                                    res._prepare_vals_self_task(res, job_order, attachment_line,
                                                                progress, True))  # Bottom subtask
                                self.set_approval_values(task, progress_line)
                                self.set_message(task, progress_line)
                                i += 1

                                progress = (progress * task.work_subtask_weightage) / 100
                                progress_line = res.env['progress.history'].sudo().create(
                                    res._prepare_vals_parent_from_subtask(res, job_order, attachment_line, progress,
                                                                          subtask))  # Parent of bottom subtask
                                self.set_approval_values(task.parent_task, progress_line)
                                # don't call self.set_message(task, progress_line) here
                                if task.parent_task:
                                    task = task.parent_task
                                else:
                                    break
                            else:
                                if task.is_subtask:
                                    if task.subtask_exist and not res.subtask and i < 1:
                                        progress_line = res.env['progress.history'].sudo().create(
                                            res._prepare_vals_self_task(res, job_order, attachment_line, progress, True))
                                        self.set_approval_values(task, progress_line)
                                        self.set_message(task, progress_line)
                                        i += 1

                                    progress = (progress * task.work_subtask_weightage) / 100
                                    progress_line = res.env['progress.history'].sudo().create(
                                        res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress,
                                                                              subtask))
                                    self.set_approval_values(task, progress_line)
                                    self.set_message(task, progress_line)
                                    if task.parent_task:
                                        task = task.parent_task
                                else:
                                    self.set_approval_values(task, progress_line)
                                    self.set_message(task, progress_line)
                                    break



    def set_approval_values(self, task, progress_line):
        progress_line.sudo()._compute_is_customer_approval_matrix()
        progress_line.sudo()._compute_approving_customer_matrix()
        progress_line.sudo().onchange_approving_matrix_lines()
        progress_line.sudo().action_request_for_approving_matrix()


    def set_message(self, task, progress_line):
        action_id = self.env.ref('equip3_construction_operation.action_view_task_inherited')
        template_id = self.env.ref('equip3_construction_operation.email_template_reminder_for_progress_approval')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=' + str(progress_line.id) + '&action=' + str(
            action_id.id) + '&view_type=form&model=project.task'

        if self.approval_matrix_ids and len(self.approval_matrix_ids[0].approvers) > 1:
            for approved_matrix_id in self.approval_matrix_ids[0].approvers:
                approver = approved_matrix_id
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': approver.partner_id.email,
                    'approver_name': approver.name,
                    'date': date.today(),
                    'url': url,
                    'code': self.number,
                }
                template_id.sudo().with_context(ctx).send_mail(task.id, True)
        else:
            approver = self.approval_matrix_ids[0].approvers[0]
            ctx = {
                'email_from': self.env.user.company_id.email,
                'email_to': approver.partner_id.email,
                'approver_name': approver.name,
                'date': date.today(),
                'url': url,
                'code': self.number,
            }
            template_id.sudo().with_context(ctx).send_mail(task.id, True)


class AttachmentsFileWiz(models.Model):
    _name= 'attachment.file.wiz'
    _description= 'Attachment Tab Wizard'
    _order= 'sequence'

    progress = fields.Many2one('progress.history.wiz', string="Progress")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date_now = fields.Datetime(string="Date")
    attachment = fields.Binary(string= 'Attachment',  widget='many2many_binary')
    name = fields.Char(string="File Name")
    file_size = fields.Integer(compute='_compute_file_size', string='File Size', store=True)
    size = fields.Char("File Size", compute="_compute_file_size", store=True)
    description = fields.Text(string="Description")

    @api.depends('attachment')
    def _compute_file_size(self):
        for rec in self:
            if rec.attachment:
                file_detail = base64.b64decode(rec.attachment)
                rec.file_size = int(len(file_detail))
                rec.size = human_size(len(file_detail))

    @api.depends('progress.attachment_ids', 'progress.attachment_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.progress.attachment_ids:
                no += 1
                l.sr_no = no
