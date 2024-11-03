import math
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from pytz import timezone


class AssetAllocation(models.Model):
    _name = 'allocation.asset'
    _description = 'Asset Allocation'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _rec_name = 'number'

    number = fields.Char(string='Allocation Number', required=True, copy=False, readonly=True,
                         states={'draft': [('readonly', True)]}, index=True, default=lambda self: _('New'))
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    create_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.uid, readonly=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company, readonly=True)
    project = fields.Many2one(comodel_name='project.project', string='Project', required=False,
                              domain="[('primary_states','=', 'progress'),('company_id', '=', company_id)]")
    asset_allocation_option = fields.Selection(related='project.asset_allocation_option', string='Duration Option')
    branch_id = fields.Many2one(related='project.branch_id', string='Branch',
                                default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids),
                                                     ('company_id', '=', self.env.company.id)])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Request For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('paused', 'Paused'),
        ('done', 'Done'),
        ('canceled', 'Sale Order Canceled')
    ], string='Status', readonly=True, copy=False, index=True, default='draft')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Group')
    job_cost_sheet = fields.Many2one('job.cost.sheet', 'Cost Sheet')
    project_budget = fields.Many2one(comodel_name='project.budget', string='Project Budget',
                                     domain="[('project_id','=', project)]")
    budgeting_period = fields.Selection(related='project.budgeting_period', string='Budgeting Period')
    job_order = fields.Many2one('project.task', string='Job Order', domain="[('project_id','=', project)]")
    schedule_method = fields.Selection([
        ('global', 'Global'),
        ('line', 'Line')], string='Schedule Method', default='global', store=True)
    # set global 
    start_date = fields.Datetime(string="Scheduled Start Date")
    end_date = fields.Datetime(string="Scheduled End Date")
    actual_start_date = fields.Datetime(string="Actual Start Date")
    actual_end_date = fields.Datetime(string="Actual End Date")
    duration = fields.Float(string='Duration', default=0)
    allocation_asset_ids = fields.One2many('allocation.asset.line', 'allocation_id', string="Allocation Asset Line")
    department_type = fields.Selection(related='project.department_type', string='Type of Department')
    # asset_allocation_option = fields.Selection(related='project.asset_allocation_option')
    is_asset_allocation_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                         compute='_is_asset_allocation_approval_matrix')

    @api.depends('project')
    def _is_asset_allocation_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_asset_allocation_approval_matrix = IrConfigParam.get_param('is_asset_allocation_approval_matrix')
        for record in self:
            record.is_asset_allocation_approval_matrix = is_asset_allocation_approval_matrix

    @api.model
    def create(self, vals):
        vals['number'] = self.env['ir.sequence'].next_by_code('asset.allocation.sequence')
        return super(AssetAllocation, self).create(vals)

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if rec.department_type == 'project':
                return {
                    'domain': {'project': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id)]}
                }
            elif rec.department_type == 'department':
                return {
                    'domain': {
                        'project': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'),
                                    ('company_id', '=', rec.company_id.id)]}
                }

    @api.onchange('project')
    def _onchange_project(self):
        for rec in self:
            for proj in rec.project:
                self.job_cost_sheet = rec.env['job.cost.sheet'].search(
                    [('project_id', '=', proj.id), ('state', '!=', 'cancelled')])
                self.analytic_tag_ids = [(6, 0, [v.id for v in proj.analytic_idz])]

    @api.onchange('start_date')
    def _onchange_start_date(self):
        for rec in self:
            if rec.start_date:
                start_date = rec.start_date.date()
                if rec.budgeting_period == 'project':
                    if start_date < rec.project.act_start_date:
                        raise ValidationError("Start Date must be greater than or equal to Actual Start Date of "
                                              "Project")
                elif rec.budgeting_period == 'monthly':
                    if rec.project_budget:
                        if start_date < rec.project_budget.month.start_date:
                            raise ValidationError("Start Date must be greater than or equal to Start "
                                                  "Date of Project Budget")
                        elif start_date >= rec.project_budget.month.end_date:
                            raise ValidationError("Start Date must be less than End Date of Project Budget")
                elif rec.budgeting_period == 'custom':
                    if rec.project_budget:
                        if start_date < rec.project_budget.bd_start_date:
                            raise ValidationError("Start Date must be greater than or equal to Start "
                                                  "Date of Project Budget")
                        elif start_date >= rec.project_budget.bd_end_date:
                            raise ValidationError("Start Date must be less than End Date of Project Budget")

    @api.onchange('end_date')
    def _onchange_end_date(self):
        for rec in self:
            if rec.end_date:
                end_date = rec.end_date.date()
                if rec.budgeting_period == 'project':
                    if end_date < rec.project.act_start_date:
                        raise ValidationError("End Date must be less than or equal to Actual Start Date of Project")
                elif rec.budgeting_period == 'monthly':
                    if rec.project_budget:
                        if end_date > rec.project_budget.month.end_date:
                            raise ValidationError("End Date must be less than or equal to End "
                                                  "Date of Project Budget")
                        elif end_date <= rec.project_budget.month.start_date:
                            raise ValidationError("End Date must be greater than Start Date of Project Budget")
                elif rec.budgeting_period == 'custom':
                    if rec.project_budget:
                        if end_date > rec.project_budget.bd_end_date:
                            raise ValidationError("End Date must be less than or equal to End "
                                                  "Date of Project Budget")
                        elif end_date <= rec.project_budget.bd_start_date:
                            raise ValidationError("End Date must be greater than Start Date of Project Budget")

    def _send_bd_data(self, bd):
        return {
            'cs_internal_asset_id': bd.cs_internal_asset_id.id,
            'bd_internal_asset_id': bd.id,
            'project_scope': bd.project_scope_line_id.id,
            'section': bd.section_name.id,
            'variable': bd.variable_id.id,
            'asset_id': bd.asset_id.id,
            'serial_number': bd.asset_id.serial_no,
        }

    def _send_cs_data(self, cs):
        return {
            'cs_internal_asset_id': cs.id,
            'project_scope': cs.project_scope.id,
            'section': cs.section_name.id,
            'variable': cs.variable_ref.id,
            'asset_id': cs.asset_id.id,
            'serial_number': cs.asset_id.serial_no,
        }

    @api.onchange('project_budget', 'job_order')
    def _onchange_project_budget(self):
        self.allocation_asset_ids = [(5, 0, 0)]
        for rec in self:
            if rec.project_budget:
                rec.update({
                    'start_date': False,
                    'end_date': False,
                })

                if rec.budgeting_period == 'custom':
                    rec.update({
                        'start_date': datetime.combine(rec.project_budget.bd_start_date, datetime.min.time()),
                        'end_date': datetime.combine(rec.project_budget.bd_end_date, datetime.min.time()),
                    })
                elif rec.budgeting_period == 'monthly':
                    rec.update({
                        'start_date': datetime.combine(rec.project_budget.month.start_date, datetime.min.time()),
                        'end_date': datetime.combine(rec.project_budget.month.end_date, datetime.min.time()),
                    })

    @api.onchange('project')
    def set_project(self):
        for res in self:
            for line in res.allocation_asset_ids:
                line.project = res.project

    @api.onchange('start_date')
    def set_start_date(self):
        for res in self:
            for line in res.allocation_asset_ids:
                line.start_date = res.start_date

    @api.onchange('job_order')
    def set_job_order(self):
        for res in self:
            for line in res.allocation_asset_ids:
                line.job_order = res.job_order

    @api.onchange('end_date')
    def set_end_date(self):
        for res in self:
            for line in res.allocation_asset_ids:
                line.end_date = res.end_date

    def button_confirm(self):
        for res in self:
            if res.job_cost_sheet.state != 'in_progress':
                raise ValidationError(
                    "The cost sheet for this project is not in the state 'in progress', please set to in progress first.")

            if res.project_budget:
                if res.project_budget.state != 'in_progress':
                    raise ValidationError(_("Please in progress the selected periodical budget first."))

            res.write({'state': 'in_progress'})

    def button_request_for_approval(self):
        for res in self:
            if res.allocation_asset_ids:
                res.write({'state': 'to_approve'})
                for line in res.allocation_asset_ids:
                    line.write({'state': 'to_approve'})
            else:
                raise ValidationError("At least one asset in allocation line")

    def button_start(self):
        for res in self:
            res.write({'state': 'in_progress',
                       'actual_start_date': datetime.now()})
            # for line in res.allocation_asset_ids:
            #     line.start()

    def button_pause(self):
        for res in self:
            res.write({'state': 'paused'})
            for line in res.allocation_asset_ids:
                line.pause()

    def button_start_again(self):
        for res in self:
            res.write({'state': 'in_progress'})
            for line in res.allocation_asset_ids:
                line.start_again()

    def button_done(self):
        for res in self:
            if not res.allocation_asset_ids:
                raise ValidationError("Please add line first")

            if res.project.asset_allocation_option == 'manual_count':
                if res.is_asset_allocation_approval_matrix == False:
                    for line in res.allocation_asset_ids:
                        if line.state == 'draft':
                            raise ValidationError("Please in progress asset allocation line first")
                        elif line.state == 'in_progress':
                            line.done()
                        else:
                            pass

                else:
                    for line in res.allocation_asset_ids:
                        if line.state in ('draft', 'in_progress', 'to_approve'):
                            raise ValidationError("Please approve asset allocation line first")
                        elif line.state == 'approved':
                            line.done()
                        else:
                            pass

                res.write({'state': 'done',
                           'actual_end_date': datetime.now()})

            else:
                res.write({'state': 'done',
                           'actual_end_date': datetime.now()})


class AssetAllocationLine(models.Model):
    _name = 'allocation.asset.line'
    _description = 'Asset Allocation Line'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char('name', compute='_compute_name')
    allocation_id = fields.Many2one(comodel_name='allocation.asset', string='Asset Allocation')
    cs_internal_asset_id = fields.Many2one(comodel_name='internal.asset',
                                           domain="[('job_sheet_id','=', job_cost_sheet), ('asset_id', '=', asset_id)]",
                                           string='Cost Sheet Budget Asset Line')
    cs_overhead_id = fields.Many2one(comodel_name='material.overhead',
                                     domain="[('job_sheet_id','=', job_cost_sheet), ('product_id', '=', "
                                            "fuel_type_id), ('overhead_catagory', '=', 'fuel')]",
                                     string='Cost Sheet Budget Overhead Line')
    bd_internal_asset_id = fields.Many2one(comodel_name='budget.internal.asset',
                                           domain="[('project_budget_id','=', project_budget), ('asset_id', '=', "
                                                  "asset_id)]", string='Periodical Budget Asset Line')
    bd_overhead_id = fields.Many2one(comodel_name='budget.overhead',
                                     domain="[('budget_id','=', project_budget), ('product_id', '=', "
                                            "fuel_type_id), ('overhead_catagory', '=', 'fuel')]",
                                     string='Periodical Budget Overhead Line')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project = fields.Many2one(related='allocation_id.project', string='Project')
    budgeting_period = fields.Selection(related='project.budgeting_period', string='Budgeting Period')
    budgeting_method = fields.Selection(related='project.budgeting_method', string='Budgeting Method')
    warehouse_location_ids = fields.One2many(related='project.warehouse_location_ids')
    source_location_id = fields.Many2one(comodel_name='stock.location', string='Source Location')
    destination_location_id = fields.Many2one(comodel_name='stock.location', string='Destination Location (Scrap)')
    fuel_type_id = fields.Many2one(comodel_name='product.product', string='Fuel Type',
                                   domain=[('type', '=', 'product')])
    uom_id = fields.Many2one(related='fuel_type_id.uom_id', string='Unit of Measure')
    fuel_qty = fields.Float('Fuel Available Quantity', default=0.00, compute="_compute_on_hand")
    # temp_fuel_qty = fields.Float('Temporary Fuel Available Quantity', compute="_compute_temp_fuel_qty")
    job_cost_sheet = fields.Many2one(related='allocation_id.job_cost_sheet', string='Cost Sheet')
    project_budget = fields.Many2one(related='allocation_id.project_budget', string='Project Budget')
    work_hour = fields.Float(string='Project Work Hour', related='project.working_hour')
    analytic_tag_ids = fields.Many2many(related='allocation_id.analytic_tag_ids', string='Analytic Group')
    job_order = fields.Many2one(related='allocation_id.job_order', string='Job Order')
    project_asset_ids = fields.Many2many('maintenance.equipment', string='Asset List', compute="_compute_asset_ids")
    project_scope = fields.Many2one('project.scope.line', string="Project Scope",
                                    domain="[('project_id','=', project)]")
    section = fields.Many2one('section.line', string="Section")
    variable = fields.Many2one('variable.template', string="Variable")
    asset_id = fields.Many2one('maintenance.equipment', string="Asset",
                               domain="[('id', 'in', project_asset_ids)]")
    is_vehicle = fields.Boolean(string='Vehicle')
    serial_number = fields.Char(string='Serial Number', copy=False, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('to_approve', 'Request For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paused', 'Paused'),
        ('done', 'Done'),
        ('canceled', 'Canceled')
    ], string='Status', readonly=True, copy=False, index=True, default='draft')
    state1 = fields.Selection(related='state', tracking=False)
    state2 = fields.Selection(related='state', tracking=False)
    state3 = fields.Selection(related='state', tracking=False)
    state4 = fields.Selection(related='state', tracking=False)
    # set line
    start_date = fields.Datetime(string="Scheduled Start Date", store="True")
    end_date = fields.Datetime(string="Scheduled End Date", store="True")
    actual_start_date = fields.Datetime(string="Actual Start Date", store="True")
    actual_end_date = fields.Datetime(string="Actual End Date", store="True")
    duration = fields.Float(string='Duration', default=0, compute='_compute_duration', inverse='_set_duration')
    time_ids = fields.One2many('asset.time.progress', 'allocation_asset_id')
    fuel_log = fields.One2many('asset.fuel.usage', 'asset_usage_id', string='Fuel Log')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company, readonly=True)
    branch_id = fields.Many2one(related='project.branch_id', string='Branch',
                                default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids),
                                                     ('company_id', '=', self.env.company.id)])
    department_type = fields.Selection(related='project.department_type', string='Type of Department')
    asset_allocation_option = fields.Selection(related='allocation_id.asset_allocation_option')

    count_asset_usage = fields.Integer(compute='_compute_count_asset_usage')
    count_asset_fuel_log = fields.Integer(compute='_compute_count_asset_fuel_log')
    count_asset_odometer = fields.Integer(compute='_compute_count_asset_odometer')
    count_asset_hour_meter = fields.Integer(compute='_compute_count_asset_hour_meter')
    delivery_order_count = fields.Integer(compute='_compute_delivery_order_count', string='Delivery Orders')

    # approval matrix
    is_asset_allocation_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                         compute='_is_asset_allocation_approval_matrix')
    approving_matrix_asset_allocation_id = fields.Many2one('approval.matrix.asset.allocation', string="Approval Matrix",
                                                           compute='_compute_approving_customer_matrix')
    asset_allocation_user_ids = fields.One2many('asset.allocation.approver.user', 'asset_allocation_approver_id',
                                                string='Approver')
    approvers_ids = fields.Many2many('res.users', 'allocation_line_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    employee_id = fields.Many2one('res.users', string='Users')
    last_approved = fields.Many2one('res.users', string='Users')

    @api.depends('project')
    def _is_asset_allocation_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_asset_allocation_approval_matrix = IrConfigParam.get_param('is_asset_allocation_approval_matrix')
        for record in self:
            record.is_asset_allocation_approval_matrix = is_asset_allocation_approval_matrix

    @api.depends('allocation_id', 'asset_id', 'project', 'branch_id', 'company_id', 'department_type', 'start_date',
                 'end_date')
    def _compute_approving_customer_matrix(self):
        for res in self:
            res.approving_matrix_asset_allocation_id = False
            if res.allocation_id:
                if res.is_asset_allocation_approval_matrix:
                    if res.department_type == 'project':
                        approving_matrix_asset_allocation_id = self.env['approval.matrix.asset.allocation'].search([
                            ('company_id', '=', res.company_id.id),
                            ('branch_id', '=', res.branch_id.id),
                            ('project_id', 'in', (res.project.id)),
                            ('department_type', '=', 'project'),
                            ('set_default', '=', False)], limit=1)

                        approving_matrix_default = self.env['approval.matrix.asset.allocation'].search([
                            ('company_id', '=', res.company_id.id),
                            ('branch_id', '=', res.branch_id.id),
                            ('set_default', '=', True),
                            ('department_type', '=', 'project')], limit=1)

                    else:
                        approving_matrix_asset_allocation_id = self.env['approval.matrix.asset.allocation'].search([
                            ('company_id', '=', res.company_id.id),
                            ('branch_id', '=', res.branch_id.id),
                            ('project_id', 'in', (res.project.id)),
                            ('department_type', '=', 'department'),
                            ('set_default', '=', False)], limit=1)

                        approving_matrix_default = self.env['approval.matrix.asset.allocation'].search([
                            ('company_id', '=', res.company_id.id),
                            ('branch_id', '=', res.branch_id.id),
                            ('set_default', '=', True),
                            ('department_type', '=', 'department')], limit=1)

                    if approving_matrix_asset_allocation_id:
                        res.approving_matrix_asset_allocation_id = approving_matrix_asset_allocation_id and approving_matrix_asset_allocation_id.id or False
                    else:
                        if approving_matrix_default:
                            res.approving_matrix_asset_allocation_id = approving_matrix_default and approving_matrix_default.id or False
                else:
                    res.approving_matrix_asset_allocation_id = False
            else:
                res.approving_matrix_asset_allocation_id = False

    @api.onchange('asset_id', 'project', 'approving_matrix_asset_allocation_id', 'start_date', 'end_date')
    def onchange_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.project:
                app_list = []
                if record.state == 'draft' and record.is_asset_allocation_approval_matrix:
                    record.asset_allocation_user_ids = []
                    for rec in record.approving_matrix_asset_allocation_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'user_ids': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                    record.approvers_ids = app_list
                    record.asset_allocation_user_ids = data

    def _compute_is_approver(self):
        for record in self:
            if record.approvers_ids:
                current_user = record.env.user
                matrix_line = sorted(record.asset_allocation_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(record.asset_allocation_user_ids)
                if app < a:
                    for line in record.asset_allocation_user_ids[app]:
                        if current_user in line.user_ids:
                            record.is_approver = True
                        else:
                            record.is_approver = False
                else:
                    record.is_approver = False
            else:
                record.is_approver = False

    def request_approval(self):
        for line in self:
            if len(line.asset_allocation_user_ids) == 0:
                raise ValidationError(
                    _("There's no asset allocation approval matrix for this project or approval matrix default created. "
                      "You have to create it first."))

            dep_cal = line.cal_amount_dep(line)
            total_hour_meter = sum(line.time_ids.mapped('hour_meter'))

            if line.budgeting_method == 'product_budget':
                if line.bd_internal_asset_id:
                    if total_hour_meter > line.bd_internal_asset_id.budgeted_qty_left:
                        raise ValidationError(_("The quantity actual is over the remaining quantity"))
                    elif dep_cal > line.bd_internal_asset_id.budgeted_amt_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                else:
                    if total_hour_meter > line.cs_internal_asset_id.budgeted_qty_left:
                        raise ValidationError(_("The quantity actual is over the remaining quantity"))
                    elif dep_cal > line.cs_internal_asset_id.budgeted_amt_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))

            elif line.budgeting_method == 'gop_budget':
                if line.bd_internal_asset_id:
                    if total_hour_meter > line.bd_internal_asset_id.budgeted_qty_left:
                        raise ValidationError(_("The quantity actual is over the remaining quantity"))
                    elif dep_cal > line.bd_internal_asset_id.budgeted_amt_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                else:
                    if total_hour_meter > line.cs_internal_asset_id.budgeted_qty_left:
                        raise ValidationError(_("The quantity actual is over the remaining quantity"))
                    elif dep_cal > line.cs_internal_asset_id.budgeted_amt_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))

            elif line.budgeting_method == 'budget_type':
                if line.bd_internal_asset_id:
                    if dep_cal > line.project_budget.amount_left_budget:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                else:
                    if dep_cal > line.job_cost_sheet.internas_budget_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))

            else:
                if line.bd_internal_asset_id:
                    if dep_cal > line.project_budget.budget_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                else:
                    if dep_cal > line.job_cost_sheet.contract_budget_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))

            if not line.time_ids:
                raise ValidationError(
                    _("There's no asset usage. "
                      "You have to add a line first."))

            action_id = self.env.ref('equip3_construction_operation.asset_allocation_line_action_const')
            template_id = self.env.ref(
                'equip3_construction_operation.email_template_reminder_for_asset_allocation_approval')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(line.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=allocation.asset.line'
            if line.asset_allocation_user_ids and len(line.asset_allocation_user_ids[0].user_ids) > 1:
                for approved_matrix_id in line.asset_allocation_user_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from': self.env.user.company_id.email,
                        'email_to': approver.partner_id.email,
                        'approver_name': approver.name,
                        'date': date.today(),
                        'url': url,
                    }
                    template_id.with_context(ctx).send_mail(line.id, True)
            else:
                approver = line.asset_allocation_user_ids[0].user_ids[0]
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': approver.partner_id.email,
                    'approver_name': approver.name,
                    'date': date.today(),
                    'url': url,
                }
                template_id.with_context(ctx).send_mail(line.id, True)

            line.write({'employee_id': self.env.user.id,
                        'state': 'to_approve',
                        })

            for line_id in line.asset_allocation_user_ids:
                line_id.write({'approver_state': 'draft'})

    def btn_approve(self):
        sequence_matrix = [data.name for data in self.asset_allocation_user_ids]
        sequence_approval = [data.name for data in self.asset_allocation_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.asset_allocation_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)

        for record in self:
            action_id = self.env.ref('equip3_construction_operation.asset_allocation_line_action_const')
            template_app = self.env.ref('equip3_construction_operation.email_template_asset_allocation_approved')
            template_id = self.env.ref(
                'equip3_construction_operation.email_template_reminder_for_asset_allocation_approval_temp')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=allocation.asset.line'

            current_user = self.env.uid
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"

            if self.env.user not in record.approved_user_ids:
                if record.is_approver:
                    for line in record.asset_allocation_user_ids:
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

                    matrix_line = sorted(record.asset_allocation_user_ids.filtered(lambda r: r.is_approve == False))
                    if len(matrix_line) == 0:
                        record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                        ctx = {
                            'email_from': self.env.user.company_id.email,
                            'email_to': record.employee_id.email,
                            'date': date.today(),
                            'url': url,
                        }
                        template_app.sudo().with_context(ctx).send_mail(record.id, True)
                        record.write({'state': 'approved'})

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
                                'url': url,
                            }
                            template_id.sudo().with_context(ctx).send_mail(record.id, True)

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
            action_id = self.env.ref('equip3_construction_operation.asset_allocation_line_action_const')
            template_rej = self.env.ref('equip3_construction_operation.email_template_asset_allocation_rejected')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=allocation.asset.line'
            for user in record.asset_allocation_user_ids:
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
            ctx = {
                'email_from': self.env.user.company_id.email,
                'email_to': record.employee_id.email,
                'date': date.today(),
                'url': url,
            }
            template_rej.sudo().with_context(ctx).send_mail(record.id, True)
            record.write({'state': 'rejected'})

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'approval.matrix.asset.allocation.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def _compute_count_asset_usage(self):
        for rec in self:
            rec.count_asset_usage = self.env['asset.usage'].search_count([('asset_allocation_line_id', '=', rec.id)])

    def _compute_count_asset_fuel_log(self):
        for rec in self:
            rec.count_asset_fuel_log = self.env['maintenance.fuel.logs'].search_count(
                [('asset_allocation_line_id', '=', rec.id)])

    def _compute_count_asset_odometer(self):
        for rec in self:
            rec.count_asset_odometer = self.env['maintenance.vehicle'].search_count(
                [('asset_allocation_line_id', '=', rec.id)])

    def _compute_count_asset_hour_meter(self):
        for rec in self:
            rec.count_asset_hour_meter = self.env['maintenance.hour.meter'].search_count(
                [('asset_allocation_line_id', '=', rec.id)])

    def _compute_delivery_order_count(self):
        for record in self:
            fuel_log_id = self.env['maintenance.fuel.logs'].search([('asset_allocation_line_id', '=', self.id)])
            fuel_log_count = 0
            for fuel in fuel_log_id:
                fuel_log_count += record.env['stock.picking'].search_count([('fuel_log_id', '=', fuel.id)])
            record.delivery_order_count = fuel_log_count

    # @api.depends('fuel_type_id', 'time_ids')
    # def _compute_temp_fuel_qty(self):
    #     for rec in self:
    #         rec.temp_fuel_qty = 0
    #         asset_allocation_line = (self.env['allocation.asset.line']
    #                                  .search([('asset_id', '=', rec.asset_id.id),
    #                                           ('fuel_type_id', '=', rec.fuel_type_id.id)]))
    #         time_ids = self.env['asset.time.progress']
    #         if len(asset_allocation_line) > 1:
    #             for asset in asset_allocation_line:
    #                 if asset.id != rec.id:
    #                     time_ids += asset.time_ids
    #         if rec.fuel_type_id and time_ids:
    #             rec.temp_fuel_qty = (rec.fuel_qty - sum(time_ids.mapped('fuel_log'))
    #                                  - sum(rec.time_ids.mapped('fuel_log')))
    #         else:
    #             rec.temp_fuel_qty = rec.fuel_qty - sum(rec.time_ids.mapped('fuel_log'))

    @api.depends('fuel_type_id', 'project.warehouse_address')
    def _compute_on_hand(self):
        for record in self:
            location_ids = []
            record.fuel_qty = 0
            if record.fuel_type_id and record.project.warehouse_address:
                location_obj = self.env['stock.location']
                store_location_id = record.project.warehouse_address.view_location_id.id
                addtional_ids = location_obj.search(
                    [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_ids.append(location.id)
                child_location_ids = self.env['stock.location'].search(
                    [('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                final_location = child_location_ids + location_ids
                # self.env.cr.execute("""
                #     SELECT SUM(available_quantity)
                #       FROM stock_quant
                #     WHERE location_id in %s AND product_id = %s
                # """ % (str(final_location).replace('[', '(').replace(']', ')'), record.fuel_type_id.id))
                # qty = self.env.cr.fetchall()
                # record.fuel_qty = qty[0][0] or 0
                record.fuel_qty = sum(self.env['stock.quant'].search(
                    [('location_id', 'in', final_location), ('product_id', '=', record.fuel_type_id.id)]).mapped(
                    'available_quantity')) or 0

    @api.onchange('allocation_id')
    def _onchange_allocation(self):
        for rec in self:
            if rec.allocation_id:
                if rec.allocation_id.state == 'draft':
                    raise ValidationError("The selected Asset Allocation is in Draft state. You may want to confirm "
                                          "it first before proceeding.")

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if rec.department_type == 'project':
                return {
                    'domain': {'project': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id)]}
                }
            elif rec.department_type == 'department':
                return {
                    'domain': {
                        'project': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'),
                                    ('company_id', '=', rec.company_id.id)]}
                }

    def _compute_name(self):
        for rec in self:
            record = rec.asset_id.name
            rec.write({'name': record})

    @api.onchange('project_scope')
    def _onchange_project_scope(self):
        for rec in self:
            same = rec.project_scope.name
            return {
                'domain': {'section': [('project_scope.name', '=', same), ('project_id', '=', rec.project.id)]}
            }

    @api.onchange('cs_internal_asset_id')
    def _onchange_asset_cs(self):
        for rec in self:
            for cs in rec.cs_internal_asset_id:
                rec.write({'project_scope': cs.project_scope.id,
                           'section': cs.section_name.id,
                           'variable': cs.variable_id.id,
                           'asset_id': cs.asset_id.id, })

    @api.onchange('bd_internal_asset_id')
    def _onchange_asset_bd(self):
        for rec in self:
            for bd in rec.bd_internal_asset_id:
                rec.write({'project_scope': bd.project_scope_line_id.id,
                           'section': bd.section_name.id,
                           'variable': bd.variable_id.id,
                           'asset_id': bd.asset_id.id, })
            if rec.bd_internal_asset_id:
                rec.update({
                    'cs_internal_asset_id': rec.bd_internal_asset_id.cs_internal_asset_id.id,
                })

    @api.onchange('bd_overhead_id')
    def _onchange_overhead_bd(self):
        for rec in self:
            if rec.bd_overhead_id:
                rec.update({
                    'cs_overhead_id': rec.bd_overhead_id.cs_overhead_id.id,
                })

    @api.onchange('start_date')
    def _onchange_start_date(self):
        for rec in self:
            if rec.start_date:
                if rec.start_date < rec.allocation_id.start_date:
                    raise ValidationError("Start Date must be greater than or equal to Scheduled Start Date of Asset "
                                          "Allocation")
                elif rec.start_date >= rec.allocation_id.end_date:
                    raise ValidationError("Start Date must be less than Scheduled End Date of Asset "
                                          "Allocation")

    @api.onchange('end_date')
    def _onchange_end_date(self):
        for rec in self:
            if rec.end_date:
                if rec.end_date > rec.allocation_id.end_date:
                    raise ValidationError("End Date must be less than or equal to Scheduled End Date of Asset "
                                          "Allocation")
                elif rec.end_date <= rec.allocation_id.start_date:
                    raise ValidationError("End Date must be greater than Scheduled Start Date of Asset "
                                          "Allocation")

    @api.onchange('time_ids')
    def _onchange_time_ids(self):
        for rec in self:
            if 2 >= len(rec.time_ids) > 0:
                rec.actual_start_date = rec.time_ids[0].date_start

    @api.depends('allocation_id.allocation_asset_ids', 'allocation_id.allocation_asset_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.allocation_id.allocation_asset_ids:
                no += 1
                l.sr_no = no

    @api.depends('asset_id', 'allocation_id')
    def _compute_asset_ids(self):
        for rec in self:
            if rec.allocation_id.project:
                rec.project_asset_ids = [(6, 0, rec.allocation_id.project.project_asset_ids.equipment_name.ids +
                                          rec.allocation_id.project.project_vehicle_ids.equipment_name.ids)]
            else:
                rec.project_asset_ids = [(6, 0, [])]

    @api.onchange('asset_id')
    def _onchange_serial(self):
        for res in self:
            res.serial_number = res.asset_id.serial_no
            if res.asset_id.vehicle_checkbox:
                res.is_vehicle = True
            else:
                res.is_vehicle = False

    @api.depends('time_ids.duration', 'state')
    def _compute_duration(self):
        for res in self:
            res.duration = sum(res.time_ids.mapped('duration'))

    def _prepare_timeline_vals(self, duration, date_start, date_end=False):
        return {
            'allocation_asset_id': self.id,
            'date_start': date_start,
            'date_end': date_end,
        }

    def add_months(self, current_date, months_to_add):
        new_date = datetime(current_date.year + (current_date.month + months_to_add - 1) // 12,
                            (current_date.month + months_to_add - 1) % 12 + 1,
                            current_date.day).date()
        return new_date

    def cal_amount_dep(self, line):
        # This method handle 5 case:
        # 1. Start date and end date in same day
        # 2. Start date and end date in different day
        # 3. Start date before depreciation date and end date in same day
        # 4. Start date before depreciation date and end date in different day
        # 5. start date and end date between more than one depreciation date
        for rec in self:
            dep_cal = 0.00
            dep_var = 0.00
            dep_val = 0.00
            dep_day_val = 0.00
            hours = 0.00
            diff = 0.00
            end_hr = 0.00
            asset_id = rec.env['account.asset.asset'].search([('equipment_id', '=', line.asset_id.id),
                                                              ('state', '=', 'open')], limit=1)
            asset_dep = False
            if asset_id:
                for time in line.time_ids:
                    end_date = time.date_end
                    asset_dep_date = asset_id.depreciation_line_ids.filtered(
                        lambda x: end_date.date() >= x.depreciation_date <= end_date.date())
                    if asset_dep_date:
                        asset_dep = asset_dep_date[-1]
                    if asset_dep:
                        if asset_dep_date[-1].depreciation_date.day - 1 == 0:
                            # depreciation_end_date = asset_dep_date[-1].depreciation_date.replace(
                            #     month=asset_dep_date[-1].depreciation_date.month + asset_id.method_period,
                            #     day=asset_dep_date[-1].depreciation_date.day)
                            depreciation_end_date = rec.add_months(asset_dep_date[-1].depreciation_date, asset_id.method_period)
                        else:
                            # depreciation_end_date = asset_dep_date[-1].depreciation_date.replace(
                            #     month=asset_dep_date[-1].depreciation_date.month + asset_id.method_period,
                            #     day=asset_dep_date[-1].depreciation_date.day - 1)
                            depreciation_end_date = rec.add_months(asset_dep_date[-1].depreciation_date,
                                                                   asset_id.method_period)
                            depreciation_end_date = depreciation_end_date.replace(day=asset_dep_date[-1].depreciation_date.day - 1)
                        depreciation_duration = (depreciation_end_date - asset_dep_date[-1].depreciation_date).days
                        # daily depreciation value
                        dep_day_val = asset_dep.amount / depreciation_duration
                        hours = line.duration
                        if time.date_start.date() == time.date_end.date():
                            if line.duration >= line.work_hour:
                                dep_var = dep_day_val
                            else:
                                dep_var = dep_day_val * (line.duration / line.work_hour)
                        else:
                            start_time = time.date_start
                            end_time = time.date_end

                            working_hour = line.work_hour

                            total_value = 0

                            duration = (end_time - start_time).days
                            if duration == 1:
                                if start_time and start_time.date() >= asset_dep.depreciation_date:
                                    temp_start_datetime = start_time
                                    temp_end_datetime = start_time.replace(hour=23, minute=59, second=59)

                                    diff = temp_end_datetime - temp_start_datetime
                                    temp_total_duration = diff.total_seconds() / 60
                                    if temp_total_duration >= working_hour:
                                        total_value += dep_day_val
                                    else:
                                        total_value += dep_day_val * (temp_total_duration / working_hour)
                                if end_time:
                                    temp_start_datetime = end_time.replace(hour=0, minute=0, second=0)
                                    temp_end_datetime = end_time

                                    diff = temp_end_datetime - temp_start_datetime
                                    temp_total_duration = diff.total_seconds() / 60
                                    if temp_total_duration >= working_hour:
                                        total_value += dep_day_val
                                    else:
                                        total_value += dep_day_val * (temp_total_duration / working_hour)
                            elif duration > 1:
                                for i in range(len(asset_dep_date)):
                                    new_start_date = None
                                    new_end_date = None
                                    new_duration = 0
                                    depreciation_duration = 0
                                    if i == 0:
                                        if start_time.date() < asset_dep_date[0].depreciation_date:
                                            if i != len(asset_dep_date) - 1:
                                                new_start_date = datetime.combine(asset_dep_date[0].depreciation_date,
                                                                                  datetime.min.time())
                                                new_end_date = datetime.combine(asset_dep_date[i + 1].depreciation_date,
                                                                                datetime.min.time()) - timedelta(days=1)

                                                depreciation_duration = (new_end_date - new_start_date).days
                                                new_duration = (new_end_date - new_start_date).days

                                            elif i == len(asset_dep_date) - 1:
                                                new_start_date = datetime.combine(asset_dep_date[0].depreciation_date,
                                                                                  datetime.min.time())
                                                new_end_date = end_time

                                                depreciation_start_date = datetime.combine(
                                                    asset_dep_date[0].depreciation_date,
                                                    datetime.min.time())
                                                if depreciation_start_date.day - 1 == 0:
                                                    # depreciation_end_date = depreciation_start_date.replace(
                                                    #     month=depreciation_start_date.month + asset_id.method_period,
                                                    #     day=depreciation_start_date.day)
                                                    depreciation_end_date = rec.add_months(
                                                        asset_dep_date[-1].depreciation_date, asset_id.method_period)
                                                else:
                                                    depreciation_end_date = depreciation_start_date.replace(
                                                        month=depreciation_start_date.month + asset_id.method_period,
                                                        day=depreciation_start_date.day)
                                                depreciation_duration = (
                                                            depreciation_end_date - depreciation_start_date).days

                                                new_duration = (new_end_date - new_start_date).days

                                    elif i != len(asset_dep_date) - 1:
                                        new_start_date = datetime.combine(asset_dep_date[i].depreciation_date,
                                                                          datetime.min.time())
                                        new_end_date = datetime.combine(asset_dep_date[i + 1].depreciation_date,
                                                                        datetime.min.time()) - timedelta(days=1)

                                        new_duration = (new_end_date - new_start_date).days
                                        depreciation_duration = (new_end_date - new_start_date).days

                                    elif i == len(asset_dep_date) - 1:

                                        if start_time.date() > asset_dep_date[i].depreciation_date:
                                            new_start_date = start_time
                                            new_end_date = end_time

                                            new_duration = (new_end_date - new_start_date).days
                                        else:
                                            new_start_date = datetime.combine(asset_dep_date[i].depreciation_date,
                                                                              datetime.min.time())
                                            new_end_date = end_time

                                            new_duration = (new_end_date - new_start_date).days

                                        depreciation_start_date = datetime.combine(asset_dep_date[i].depreciation_date,
                                                                                   datetime.min.time())
                                        if depreciation_start_date.day - 1 == 0:
                                            # depreciation_end_date = depreciation_start_date.replace(
                                            #     month=depreciation_start_date.month + asset_id.method_period,
                                            #     day=depreciation_start_date.day)
                                            depreciation_end_date = depreciation_start_date.replace(
                                                month=rec.add_months(depreciation_start_date, asset_id.method_period).month,
                                                day=depreciation_start_date.day)
                                        else:
                                            # depreciation_end_date = depreciation_start_date.replace(
                                            #     month=depreciation_start_date.month + asset_id.method_period,
                                            #     day=depreciation_start_date.day - 1)
                                            depreciation_end_date = rec.add_months(asset_dep_date[-1].depreciation_date,
                                                                                   asset_id.method_period)
                                            depreciation_end_date = depreciation_end_date.replace(
                                                day=asset_dep_date[-1].depreciation_date.day - 1)
                                        depreciation_duration = (depreciation_end_date - depreciation_start_date.date()).days

                                    if depreciation_duration:
                                        dep_day_val = asset_dep_date[i].amount / depreciation_duration

                                    if new_start_date:
                                        temp_start_datetime = new_start_date
                                        temp_end_datetime = temp_start_datetime.replace(hour=23, minute=59, second=59)

                                        diff = temp_end_datetime - temp_start_datetime
                                        temp_total_duration = diff.total_seconds() / 60
                                        if temp_total_duration >= working_hour:
                                            total_value += dep_day_val
                                        else:
                                            total_value += dep_day_val * (temp_total_duration / working_hour)
                                    if new_end_date:
                                        temp_start_datetime = new_end_date.replace(hour=0, minute=0, second=0)
                                        temp_end_datetime = new_end_date

                                        diff = temp_end_datetime - temp_start_datetime
                                        temp_total_duration = diff.total_seconds() / 60
                                        if temp_total_duration >= working_hour:
                                            total_value += dep_day_val
                                        else:
                                            total_value += dep_day_val * (temp_total_duration / working_hour)

                                    temp_duration = new_duration - 2

                                    if temp_duration:
                                        total_value += dep_day_val * temp_duration

                            dep_var += total_value
                        dep_val += dep_var

                dep_cal = dep_val
                return dep_cal
            else:
                return 0.0

    def update_cost_value(self, res_qty, res_amt):
        return {
            'actual_used_qty': res_qty,
            'actual_used_amt': res_amt,
        }

    def update_asset_cs(self, line, dep_cal):
        total_hour_meter = sum(line.time_ids.mapped('hour_meter'))
        res_qty = line.cs_internal_asset_id.actual_used_qty + total_hour_meter
        res_amt = line.cs_internal_asset_id.actual_used_amt + dep_cal
        if self.allocation_id:
            for cs in self.allocation_id.job_cost_sheet:
                cs.internal_asset_ids = [(1, line.cs_internal_asset_id.id, self.update_cost_value(res_qty, res_amt))]
        else:
            for cs in self.job_cost_sheet:
                cs.internal_asset_ids = [(1, line.cs_internal_asset_id.id, self.update_cost_value(res_qty, res_amt))]

    def update_asset_bd(self, line, dep_cal):
        total_hour_meter = sum(line.time_ids.mapped('hour_meter'))
        res_qty = line.bd_internal_asset_id.actual_used_qty + total_hour_meter
        res_amt = line.bd_internal_asset_id.actual_used_amt + dep_cal
        if self.allocation_id:
            for bd in self.allocation_id.project_budget:
                bd.budget_internal_asset_ids = [
                    (1, line.bd_internal_asset_id.id, self.update_cost_value(res_qty, res_amt))]
        else:
            for bd in self.project_budget:
                bd.budget_internal_asset_ids = [
                    (1, line.bd_internal_asset_id.id, self.update_cost_value(res_qty, res_amt))]

    def set_actual_usage(self):
        for line in self:
            dep_cal = self.cal_amount_dep(line)
            total_hour_meter = sum(line.time_ids.mapped('hour_meter'))

            if self.budgeting_method == 'product_budget':
                if self.bd_internal_asset_id:
                    if total_hour_meter > self.bd_internal_asset_id.budgeted_qty_left:
                        raise ValidationError(_("The quantity actual is over the remaining quantity"))
                    elif dep_cal > self.bd_internal_asset_id.budgeted_amt_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                    else:
                        line.update_asset_cs(line, dep_cal)
                        line.update_asset_bd(line, dep_cal)
                else:
                    if total_hour_meter > self.cs_internal_asset_id.budgeted_qty_left:
                        raise ValidationError(_("The quantity actual is over the remaining quantity"))
                    elif dep_cal > self.cs_internal_asset_id.budgeted_amt_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                    else:
                        line.update_asset_cs(line, dep_cal)

            elif self.budgeting_method == 'gop_budget':
                if self.bd_internal_asset_id:
                    if total_hour_meter > self.bd_internal_asset_id.budgeted_qty_left:
                        raise ValidationError(_("The quantity actual is over the remaining quantity"))
                    elif dep_cal > self.bd_internal_asset_id.budgeted_amt_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                    else:
                        line.update_asset_cs(line, dep_cal)
                        line.update_asset_bd(line, dep_cal)
                else:
                    if total_hour_meter > self.cs_internal_asset_id.budgeted_qty_left:
                        raise ValidationError(_("The quantity actual is over the remaining quantity"))
                    elif dep_cal > self.cs_internal_asset_id.budgeted_amt_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                    else:
                        line.update_asset_cs(line, dep_cal)

            elif self.budgeting_method == 'budget_type':
                if self.bd_internal_asset_id:
                    if dep_cal > self.project_budget.amount_left_budget:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                    else:
                        line.update_asset_cs(line, dep_cal)
                        line.update_asset_bd(line, dep_cal)
                else:
                    if dep_cal > self.job_cost_sheet.internas_budget_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                    else:
                        line.update_asset_cs(line, dep_cal)

            else:
                if self.bd_internal_asset_id:
                    if dep_cal > self.project_budget.budget_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                    else:
                        line.update_asset_cs(line, dep_cal)
                        line.update_asset_bd(line, dep_cal)
                else:
                    if dep_cal > self.job_cost_sheet.contract_budget_left:
                        raise ValidationError(_("The amount actual amount is over the remaining amount"))
                    else:
                        line.update_asset_cs(line, dep_cal)

    def prepare_vals(self, fuel_line, fuel_type):
        return {
            'date': datetime.now(),
            'refueling_schema': fuel_type,
            'vehicle': fuel_line.asset_usage_id.asset_id.id,
            'location_id': fuel_line.location_id.id,
            'location_dest_id': fuel_line.location_dest_id.id,
            'fuel_type': fuel_line.fuel_type.id,
            'liter': fuel_line.liter,
            'total_price': fuel_line.total_price
        }

    def send_fuel_log(self):
        for line in self:
            for fuel_line in line.fuel_log:
                if fuel_line.refuel_type == 'stock':
                    fuel_type = 'fuel_stock'
                else:
                    fuel_type = 'gas_station'
                fuel_id = self.env['maintenance.fuel.logs'].create(line.prepare_vals(fuel_line, fuel_type))
                fuel_id.action_confirm()

    def _set_duration(self):
        def _float_duration_to_second(duration):
            minutes = duration // 1
            seconds = (duration % 1) * 60
            return minutes * 60 + seconds

        for order in self:
            old_order_duation = sum(order.time_ids.mapped('duration'))
            new_order_duration = order.duration
            if new_order_duration == old_order_duation:
                continue

            delta_duration = new_order_duration - old_order_duation

            if delta_duration > 0:
                date_start = datetime.now() - timedelta(seconds=_float_duration_to_second(delta_duration))
                self.env['asset.time.progress'].create(
                    order._prepare_timeline_vals(delta_duration, date_start, datetime.now())
                )
            else:
                duration_to_remove = abs(delta_duration)
                timelines = order.time_ids.sorted(lambda t: t.date_start)
                timelines_to_unlink = self.env['asset.time.progress']
                for timeline in timelines:
                    if duration_to_remove <= 0.0:
                        break
                    if timeline.duration <= duration_to_remove:
                        duration_to_remove -= timeline.duration
                        timelines_to_unlink |= timeline
                    else:
                        new_time_line_duration = timeline.duration - duration_to_remove
                        timeline.date_start = timeline.date_end - timedelta(
                            seconds=_float_duration_to_second(new_time_line_duration))
                        break
                timelines_to_unlink.unlink()

    def button_confirm(self):
        for res in self:
            res.write({'state': 'in_progress'})

    def start(self):
        for res in self:
            res.write({'state': 'in_progress',
                       'actual_start_date': datetime.now()})
            res.env['asset.time.progress'].create(
                res._prepare_timeline_vals(res.duration, datetime.now())
            )

    def pause(self):
        for res in self:
            res.write({'state': 'paused'})
            time_ids = res.time_ids.filtered(lambda r: not r.date_end)
            if time_ids:
                time_ids.write({'date_end': datetime.now()})

    def start_again(self):
        for res in self:
            res.write({'state': 'in_progress'})
            res.env['asset.time.progress'].create(
                res._prepare_timeline_vals(res.duration, datetime.now())
            )

    def prepare_vals_hour(self, hour):
        total_value = sum(self.env['maintenance.hour.meter'].search([]).mapped('value'))
        return {
            'date': datetime.now(),
            'maintenance_asset': hour.allocation_asset_id.asset_id.id,
            'value': hour.hour_meter,
            'total_value': hour.hour_meter + total_value,
        }

    def send_hour_log(self):
        for rec in self:
            for hour in rec.time_ids:
                hour_id = self.env['maintenance.hour.meter'].create(rec.prepare_vals_hour(hour))

    def prepare_vals_odo(self, rec):
        return {
            'date': datetime.now(),
            'vehicle': rec.asset_id.id,
            'value': rec.time_ids.distance,
        }

    def send_odo_log(self):
        for rec in self:
            for odo in rec.time_ids:
                odo_id = self.env['maintenance.vehicle'].create(rec.prepare_vals_odo(rec))

    def done(self):
        for rec in self:
            if not rec.time_ids:
                raise ValidationError(
                    _("There's no asset usage. "
                      "You have to add a line first."))

            total_fuel_log = sum(rec.time_ids.mapped('fuel_log'))
            if total_fuel_log > rec.fuel_qty:
                raise ValidationError("Total fuel log must be less than or equal to On Hand Fuel Quantity")

            used_amt = total_fuel_log * rec.fuel_type_id.standard_price

            rec.write({'state': 'done',
                       'actual_end_date': datetime.now()})

            rec.set_actual_usage()

            asset_usage_line_vals = []

            if rec.is_vehicle:
                if rec.budgeting_method == 'product_budget':
                    if rec.bd_overhead_id and rec.cs_overhead_id:
                        if total_fuel_log > self.bd_overhead_id.unused_qty:
                            raise ValidationError(_("Total fuel log is over the budget quantity."))
                        if used_amt > self.bd_overhead_id.unused_amt:
                            raise ValidationError(_("Total amount fuel is over the budget amount."))
                    elif not rec.bd_overhead_id and rec.cs_overhead_id:
                        if total_fuel_log > self.cs_overhead_id.unused_qty:
                            raise ValidationError(_("Total fuel log is over the budget quantity."))
                        if used_amt > self.cs_overhead_id.unused_amt:
                            raise ValidationError(_("Total amount fuel is over the budget amount."))

                for usage in rec.time_ids:
                    asset_usage_line_vals.append((0, 0, {
                        'equipment_id': rec.asset_id.id,
                        'start_time': usage.date_start,
                        'end_time': usage.date_end,
                        'operator_id': usage.operator_id.id,
                        'activity_type': 'operative',
                        'fuel_usage': usage.fuel_log,
                        'odometer': usage.odometer,
                        'hour_meter': usage.hour_meter,

                    }))
                asset_usage = rec.env['asset.usage'].create({
                    'asset_allocation_line_id': rec.id,
                    'name': rec.project.name + ' - ' + rec.asset_id.name + ' - ' + rec.actual_start_date.strftime(
                        DEFAULT_SERVER_DATETIME_FORMAT),
                    'facility_id': rec.asset_id.fac_area.id,
                    'equipment_ids': [(6, 0, [rec.asset_id.id])],
                    'start_date': rec.actual_start_date,
                    'branch_id': rec.project.branch_id.id,
                    'vehicle_usage_line': asset_usage_line_vals,
                })

                asset_usage.action_confirm()
                rec.asset_usage_action_done(asset_usage)
            else:
                for usage in rec.time_ids:
                    asset_usage_line_vals.append((0, 0, {
                        'equipment_id': rec.asset_id.id,
                        'start_time': usage.date_start,
                        'end_time': usage.date_end,
                        'operator_id': usage.operator_id.id,
                        'activity_type': 'operative',
                        'hour_meter': usage.hour_meter,
                    }))

                asset_usage = rec.env['asset.usage'].create({
                    'asset_allocation_line_id': rec.id,
                    'name': rec.project.name + ' - ' + rec.asset_id.name + ' - ' + rec.actual_start_date.strftime(
                        DEFAULT_SERVER_DATETIME_FORMAT),
                    'facility_id': rec.asset_id.fac_area.id,
                    'equipment_ids': [(6, 0, [rec.asset_id.id])],
                    'start_date': rec.actual_start_date,
                    'branch_id': rec.project.branch_id.id,
                    'asset_usage_line': asset_usage_line_vals,
                })
                asset_usage.action_confirm()
                rec.asset_usage_action_done(asset_usage)

    def _prepare_maintenance_hour_meter(self, equipment_id, end_time, hour_meter_value):
        """
        Prepare a maintenance hour meter record for the given asset with the given values
        """
        if hour_meter_value > 0:
            vals = {
                'asset_allocation_line_id': self.id,
                'maintenance_asset': equipment_id,
                'date': end_time,
                'value': hour_meter_value,
                'total_value': hour_meter_value,
            }
            return vals

    def _prepare_maintenance_odometer(self, equipment_id, end_time, odometer_value, unit):
        """
        Prepare a maintenance odometer record for the given vehicle with the given values
        """
        if odometer_value > 0:
            vals = {
                'asset_allocation_line_id': self.id,
                'maintenance_vehicle': equipment_id,
                'date': end_time,
                'total_value': odometer_value,
                'unit': unit
            }
            return vals

    def asset_usage_action_done(self, asset):
        for rec in self:
            maintenance_hour_meter = []
            maintenance_odometer = []

            for asset_usage in rec.time_ids:
                hour_meter_vals_vehicle = rec._prepare_maintenance_hour_meter(rec.asset_id.id,
                                                                              asset_usage.date_end,
                                                                              asset_usage.hour_meter)
                if hour_meter_vals_vehicle:
                    maintenance_hour_meter.append(hour_meter_vals_vehicle)

                odometer_vals_vehicle = rec._prepare_maintenance_odometer(rec.asset_id.id,
                                                                          asset_usage.date_end,
                                                                          asset_usage.odometer,
                                                                          asset_usage.unit)
                if odometer_vals_vehicle:
                    maintenance_odometer.append(odometer_vals_vehicle)

            for vehicle_usage in asset.vehicle_usage_line:
                # for create maintenance_fuel_logs
                if rec.fuel_type_id:
                    equip_fuel_logs = asset.env['maintenance.fuel.logs'].search(
                        [('vehicle', '=', vehicle_usage.equipment_id.id)], limit=1, order='id DESC')
                    fuel_log = asset.env['maintenance.fuel.logs'].create({
                        'asset_allocation_line_id': rec.id,
                        'vehicle': vehicle_usage.equipment_id.id,
                        'date': vehicle_usage.end_time,
                        'fuel_type': rec.fuel_type_id.id,
                        'fuel_usage': vehicle_usage.fuel_usage,
                        'liter': vehicle_usage.fuel_usage,
                        'current_fuel': equip_fuel_logs.current_fuel - vehicle_usage.fuel_usage,
                        'odometer': vehicle_usage.odometer,
                        'hour_meter': vehicle_usage.hour_meter,
                        'refueling_schema': 'fuel_stock',
                        'location_id': rec.source_location_id.id,
                        'location_dest_id': rec.destination_location_id.id,
                        'analytic_group': rec.analytic_tag_ids.ids,
                    })
                    rec.fuel_logs_action_confirm(fuel_log)

            if maintenance_hour_meter:
                asset.env['maintenance.hour.meter'].create(maintenance_hour_meter)

            if maintenance_odometer:
                asset.env['maintenance.vehicle'].create(maintenance_odometer)

            asset.write({'state': 'done'})
            asset.asset_usage_line.write({'state': 'done'})
            asset.vehicle_usage_line.write({'state': 'done'})

    def fuel_logs_action_confirm(self, fuel_log):
        for rec in self:
            if fuel_log.refueling_schema == 'fuel_stock':
                fuel_log.state = 'confirm'
                available_quantity = 0
                stock_quants = fuel_log.env['stock.quant'].search([('location_id', '=', fuel_log.location_id.id),
                                                                   ('product_id', '=', fuel_log.fuel_type.id)])
                for stock in stock_quants:
                    available_quantity += stock.available_quantity

                if fuel_log.liter > available_quantity:
                    raise ValidationError(_("There\'s not enough stock of %s in %s", fuel_log.fuel_type.display_name,
                                            fuel_log.location_id.display_name))
                else:
                    try:
                        stock_picking = fuel_log.env['stock.picking'].create({
                            'fuel_log_id': fuel_log.id,
                            'picking_type_id': fuel_log.env.ref('stock.picking_type_out').id,
                            'location_id': fuel_log.location_id.id,
                            'location_dest_id': fuel_log.location_dest_id.id,
                            'analytic_account_group_ids': [(6, 0, fuel_log.analytic_group.ids)],
                            'origin': fuel_log.name,
                            'company_id': fuel_log.env.user.company_id.id,
                            'branch_id': fuel_log.vehicle.branch_id.id,
                            'temp_allocation_datetime': fuel_log.date,
                            'asset_allocation_line_id': fuel_log.asset_allocation_line_id.id,
                        })

                        stock_move = fuel_log.env['stock.move'].create({
                            'picking_id': stock_picking.id,
                            'name': fuel_log.name,
                            'product_id': fuel_log.fuel_type.id,
                            'product_uom_qty': fuel_log.liter,
                            'product_uom': fuel_log.fuel_type.uom_id.id,
                            'location_id': fuel_log.location_id.id,
                            'location_dest_id': fuel_log.location_dest_id.id,
                            'analytic_account_group_ids': [(6, 0, fuel_log.analytic_group.ids)],
                            'scheduled_date': fuel_log.date,
                            'quantity_done': fuel_log.liter,
                            'asset_allocation_line_id': fuel_log.asset_allocation_line_id.id,
                        })
                        stock_move.write({
                            'scheduled_date': fuel_log.date,
                        })

                        stock_picking.action_confirm()
                        stock_picking.action_assign()

                        fuel_log.state = 'confirm'
                    except Exception as e:
                        raise ValidationError(_('Error!\n%s') % e)

    # purposely not using unlink to enable confirmation on delete line
    def button_delete(self):
        for rec in self:
            rec.unlink()

    def unlink(self):
        for rec in self:
            asset_usage = self.env['asset.usage'].search([('asset_allocation_line_id', '=', rec.id)])
            fuel_log = self.env['maintenance.fuel.logs'].search([('asset_allocation_line_id', '=', rec.id)])
            hour_meter = self.env['maintenance.hour.meter'].search([
                ('asset_allocation_line_id', '=', rec.id)])
            odometer = self.env['maintenance.vehicle'].search([
                ('asset_allocation_line_id', '=', rec.id)])
            stock_picking = self.env['stock.picking'].search([('asset_allocation_line_id', '=', rec.id)])
            stock_move = self.env['stock.move'].search([('asset_allocation_line_id', '=', rec.id)])
            if stock_picking:
                if stock_picking.state not in ['cancel', 'draft']:
                    raise ValidationError("You cannot delete this record because Stock Picking state is not Draft or "
                                          "Cancel (You may change it from Stock Picking before deleting)")
                stock_picking.with_context({'is_delete_from_asset_allocation_line': True}).unlink()
            if stock_move:
                stock_move.with_context({'is_delete_from_asset_allocation_line': True}).unlink()
            if asset_usage:
                asset_usage.with_context({'is_delete_from_asset_allocation_line': True}).unlink()
            if fuel_log:
                fuel_log.with_context({'is_delete_from_asset_allocation_line': True}).unlink()
            if hour_meter:
                hour_meter.with_context({'is_delete_from_asset_allocation_line': True}).unlink()
            if odometer:
                odometer.with_context({'is_delete_from_asset_allocation_line': True}).unlink()
        return super(AssetAllocationLine, self).unlink()

    def action_asset_usage(self):
        return {
            'name': "Asset Usage",
            'view_mode': 'tree,form',
            'res_model': 'asset.usage',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('asset_allocation_line_id', '=', self.id)],
        }

    def action_asset_fuel_log(self):
        return {
            'name': "Fuel Logs",
            'view_mode': 'tree,form',
            'res_model': 'maintenance.fuel.logs',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('asset_allocation_line_id', '=', self.id)],
        }

    def action_show_delivery_order(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        fuel_log_id = self.env['maintenance.fuel.logs'].search([('asset_allocation_line_id', '=', self.id)])
        action['domain'] = [('fuel_log_id', '=', fuel_log_id.ids)]
        return action

    def action_asset_odometer(self):
        return {
            'name': "Odometer",
            'view_mode': 'tree',
            'res_model': 'maintenance.vehicle',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('asset_allocation_line_id', '=', self.id)],
        }

    def action_asset_hour_meter(self):
        return {
            'name': "Odometer",
            'view_mode': 'tree',
            'res_model': 'maintenance.hour.meter',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('asset_allocation_line_id', '=', self.id)],
        }


class AssetAllocationApproverUser(models.Model):
    _name = 'asset.allocation.approver.user'
    _description = 'Asset Allocation Approver User'

    asset_allocation_approver_id = fields.Many2one('allocation.asset.line', string="Asset Allocation Line")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'asset_allocation_app_emp_ids', string="Approved user")
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
    matrix_user_ids = fields.Many2many('res.users', 'asset_allo_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    # parent status
    state = fields.Selection(related='asset_allocation_approver_id.state', string='Parent Status')

    @api.depends('asset_allocation_approver_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.asset_allocation_approver_id.asset_allocation_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len(rec.user_ids) < rec.minimum_approver and rec.asset_allocation_approver_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.asset_allocation_approver_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids


class FuelAssetUsage(models.Model):
    _name = 'asset.fuel.usage'
    _description = 'Asset Fuel Log'

    asset_usage_id = fields.Many2one(comodel_name='allocation.asset.line')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    asset_id = fields.Many2one('maintenance.equipment', string="Asset")
    refuel_type = fields.Selection([
        ('stock', 'Fuel Stock'),
        ('station', 'Gas Station')
    ], string='Refueling Schema')
    location_id = fields.Many2one('stock.location', string="Source Location")
    location_dest_id = fields.Many2one('stock.location', string="Destination Location")
    fuel_type = fields.Many2one('product.product', string="Fuel Type")
    liter = fields.Float('Liter', store=True)
    total_price = fields.Float('Total Price', store=True)

    @api.depends('asset_usage_id.fuel_log', 'asset_usage_id.fuel_log.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.asset_usage_id.fuel_log:
                no += 1
                l.sr_no = no


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    temp_allocation_datetime = fields.Datetime('Allocation Date Time', default=False)
    asset_allocation_line_id = fields.Many2one('allocation.asset.line', string='Asset Allocation Line',
                                               ondelete="restrict")

    def unlink(self):
        for rec in self:
            if rec.asset_allocation_line_id:
                if 'is_delete_from_asset_allocation_line' not in self.env.context:
                    raise ValidationError("You cannot delete this record because it is used in Asset Allocation Line "
                                          "(You may delete it from Asset Allocation Line)")
                if ('is_delete_from_asset_allocation_line' in self.env.context
                        and rec.asset_allocation_line_id.state not in ['draft', 'cancel']):
                    raise ValidationError("You cannot delete this record because it is used in Asset Allocation Line "
                                          "(You may delete it from Asset Allocation Line)")
        return super(StockPicking, self).unlink()

    @api.depends('move_lines.state', 'move_lines.date', 'move_type')
    def _compute_scheduled_date(self):
        for picking in self:
            if picking.temp_allocation_datetime:
                picking.scheduled_date = picking.temp_allocation_datetime
            else:
                moves_dates = picking.move_lines.filtered(lambda move: move.state not in ('done', 'cancel')).mapped(
                    'date')
                if picking.move_type == 'direct':
                    picking.scheduled_date = min(moves_dates, default=picking.scheduled_date or fields.Datetime.now())
                else:
                    picking.scheduled_date = max(moves_dates, default=picking.scheduled_date or fields.Datetime.now())

                return super(StockPicking, self)._compute_scheduled_date()

    def button_validate(self):
        for rec in self:
            overhead_budget = rec.asset_allocation_line_id.bd_overhead_id
            overhead_cost_sheet = rec.asset_allocation_line_id.cs_overhead_id
            for line in rec.move_ids_without_package:
                if overhead_budget:
                    overhead_budget.write({
                        'qty_used': overhead_budget.qty_used + line.quantity_done,
                        'amt_used': overhead_budget.amt_used + (
                                line.quantity_done * overhead_budget.product_id.standard_price),
                    })
                if overhead_cost_sheet:
                    overhead_cost_sheet.write({
                        'actual_used_qty': overhead_cost_sheet.actual_used_qty + line.quantity_done,
                        'actual_used_amt': overhead_cost_sheet.actual_used_amt + (
                                line.quantity_done * overhead_cost_sheet.product_id.standard_price),
                    })
        return super(StockPicking, self).button_validate()


class StockMove(models.Model):
    _inherit = 'stock.move'

    asset_allocation_line_id = fields.Many2one('allocation.asset.line', string='Asset Allocation Line',
                                               ondelete="restrict")

    def unlink(self):
        for rec in self:
            if rec.asset_allocation_line_id:
                if 'is_delete_from_asset_allocation_line' not in self.env.context:
                    raise ValidationError("You cannot delete this record because it is used in Asset Allocation Line "
                                          "(You may delete it from Asset Allocation Line)")
        return super(StockMove, self).unlink()
