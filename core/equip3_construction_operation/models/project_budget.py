from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import ValidationError
from pytz import timezone
from lxml import etree


class ProjectBudget(models.Model):
    _name = 'project.budget'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Periodical Budget"

    name = fields.Char(string="Name", default="New")
    char_name = fields.Char(string="Short Name")
    active = fields.Boolean(string='Active', default=True)
    ba_freeze_project_budget = fields.Boolean('Freeze Budget')
    state = fields.Selection(
        [('draft', 'Draft'), ('to_approve', 'Waiting for Approval'), ('approved', 'Approved'),
         ('in_progress', 'In Progress'), ('complete', 'Complete'), ('rejected', 'Reject'), ('freeze', 'Freeze'),
         ('cancelled', 'Cancelled')], string="State", readonly=True, tracking=True, default='draft')
    state1 = fields.Selection(related='state', tracking=False)
    state2 = fields.Selection(related='state', tracking=False)
    state3 = fields.Selection(related='state', tracking=False)
    state4 = fields.Selection(related='state', tracking=False)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', oldname='currency', string="Currency")
    project_id = fields.Many2one('project.project', string='Project', required=True,
                                 domain="[('primary_states','=', 'progress'), ('budgeting_period','!=', 'project')]")
    project_scope_ids = fields.Many2many('project.scope.line', string='Project Scope')
    section_ids = fields.Many2many('section.line', string='Section')
    cost_sheet = fields.Many2one('job.cost.sheet', 'Cost Sheet', required=True)
    analytic_group_id = fields.Many2many('account.analytic.tag', string='Analytic Group')
    bd_start_date = fields.Date('Budget Start Date')
    bd_end_date = fields.Date('Budget End Date')
    period = fields.Many2one('project.budget.period')
    month = fields.Many2one('budget.period.line')
    budgeting_method = fields.Selection([
        ('product_budget', 'Based on Product Budget'),
        ('gop_budget', 'Based on Group of Product Budget'),
        ('budget_type', 'Based on Budget Type'),
        ('total_budget', 'Based on Total Budget')], string='Budgeting Method', related='project_id.budgeting_method',
        store=True)
    budgeting_period = fields.Selection([
        ('project', 'Project Length Budgeting'),
        ('monthly', 'Monthly Budgeting'),
        ('custom', 'Custom Time Budgeting'), ], string='Budgeting Period', related='project_id.budgeting_period',
        store=True)
    budget_amount_total = fields.Float(string='Total Cost', readonly=True, compute='_amount_total',
                                       store=True)
    actual_amount_total = fields.Float(string='Total Actual Used Amount', readonly=True, compute='_act_amount_total',
                                       store=True)
    transferred_amount_total = fields.Float(string='Total Tranferred Amount', readonly=True,
                                            compute='_tra_amount_total', store=True)
    purchased_amount_total = fields.Float(string='Total Purchased Amount', readonly=True, compute='_pur_amount_total',
                                          store=True)
    total_period_budget = fields.Float(string='Total Budget', readonly=True)
    initial_budget_amount = fields.Float(string='Initial Budget', default=0.00)
    # Budget table
    budget_material_ids = fields.One2many('budget.material', 'budget_id')
    budget_labour_ids = fields.One2many('budget.labour', 'budget_id')
    budget_subcon_ids = fields.One2many('budget.subcon', 'budget_id')
    budget_internal_asset_ids = fields.One2many('budget.internal.asset', 'project_budget_id', string='Internal Asset')
    budget_overhead_ids = fields.One2many('budget.overhead', 'budget_id')
    budget_equipment_ids = fields.One2many('budget.equipment', 'budget_id')
    # GOP budget table
    budget_material_gop_ids = fields.One2many('budget.gop.material', 'budget_id')
    budget_labour_gop_ids = fields.One2many('budget.gop.labour', 'budget_id')
    budget_overhead_gop_ids = fields.One2many('budget.gop.overhead', 'budget_id')
    budget_equipment_gop_ids = fields.One2many('budget.gop.equipment', 'budget_id')
    # table internal transfer budget
    history_itb_bud_ids = fields.One2many('bud.internal.transfer.budget.history', 'project_budget_id',
                                          string='Change Request History')
    itb_line_bud_ids = fields.One2many('bud.internal.transfer.budget.line', 'project_budget_id',
                                       string='Change Request Line')
    budget_transfer_line_ids = fields.One2many('budget.transfer.line', 'project_budget_id', string='Budget Transfer')
    history_bt_ids = fields.One2many('budget.transfer.history', 'project_budget_id', string='Budget Transfer History')
    budget_change_allocation_line_ids = fields.One2many('budget.change.allocation.line', 'project_budget_id',
                                                        'Budget Change Allocation')
    budget_change_allocation_history_ids = fields.One2many('budget.change.allocation.history',
                                                           'project_budget_id', 'Budget Change Allocation History',
                                                           )
    material_budget_carry_over_history_ids = fields.One2many('material.budget.carry.over.history', 'project_budget_id',
                                                    string='Material Carry Over')
    labour_budget_carry_over_history_ids = fields.One2many('labour.budget.carry.over.history', 'project_budget_id',
                                                    string='Labour Carry Over')
    overhead_budget_carry_over_history_ids = fields.One2many('overhead.budget.carry.over.history', 'project_budget_id',
                                                    string='Overhead Carry Over')
    equipment_budget_carry_over_history_ids = fields.One2many('equipment.budget.carry.over.history', 'project_budget_id',
                                                    string='Equipment Carry Over')
    internal_asset_budget_carry_over_history_ids = fields.One2many('internal.asset.budget.carry.over.history', 'project_budget_id',
                                                    string='Internal Asset Carry Over')
    subcon_budget_carry_over_history_ids = fields.One2many('subcon.budget.carry.over.history', 'project_budget_id',
                                                    string='Subcon Carry Over')
    material_budget_claim_history_ids = fields.One2many('budget.claim.history', 'project_budget_id',
                                                        'Claimed Budget Left History',
                                                        domain=[('type', '=', 'material')])
    labour_budget_claim_history_ids = fields.One2many('budget.claim.history', 'project_budget_id',
                                                      'Claimed Budget Left History', domain=[('type', '=', 'labour')])
    overhead_budget_claim_history_ids = fields.One2many('budget.claim.history', 'project_budget_id',
                                                        'Claimed Budget Left History',
                                                        domain=[('type', '=', 'overhead')])
    equipment_budget_claim_history_ids = fields.One2many('budget.claim.history', 'project_budget_id',
                                                         'Claimed Budget Left History',
                                                         domain=[('type', '=', 'equipment')])
    subcon_budget_claim_history_ids = fields.One2many('budget.claim.history', 'project_budget_id',
                                                      'Claimed Budget Left History', domain=[('type', '=', 'subcon')])

    # amount material
    amount_reserved_material = fields.Monetary(compute='_compute_amount_reserved_material',
                                               string='Material Budget Reserved', readonly=True)
    amount_purchased_material = fields.Monetary(compute='_compute_amount_purchased_material',
                                                string='Material Budget Purchased', readonly=True)
    amount_transferred_material = fields.Monetary(compute='_compute_amount_transferred_material',
                                                  string='Material Budget Transferred', readonly=True)
    amount_used_material = fields.Monetary(compute='_compute_amount_used_material', string='Material Budget Used',
                                           readonly=True)
    amount_left_material = fields.Monetary(compute='_compute_amount_left_material', string='Material Budget Left',
                                           readonly=True)
    amount_material = fields.Monetary(compute='_compute_amount_material', string='Material Cost', readonly=True)
    amount_unused_material = fields.Monetary(compute='_compute_unused_material', string='Material Unused',
                                             readonly=True)
    # amount internal budget transfer
    amount_free = fields.Float(string='Available Budget Amount', readonly=True, related="cost_sheet.amount_free")
    amount_from_adjusted = fields.Float(string='Amount From Adjustment', readonly=True,
                                        compute='_amount_free_adjusted')
    amount_from_project = fields.Float(string='Amount From Other Period(+)', readonly=True,
                                       compute='_amount_free_project')
    amount_send_project = fields.Float(string='Amount Send to Other Period(-)', readonly=True,
                                       compute='_amount_send_project')

    # warehouse
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', related='project_id.warehouse_address',
                                   readonly=True)
    # boolean
    is_project_budget = fields.Boolean("Is Project Budget", default=False)
    branch_id = fields.Many2one('res.branch', string='Branch', related='project_id.branch_id')
    created_date = fields.Date('Creation Date', default=fields.Date.today, readonly=True)
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')

    # approval matrix
    approval_matrix_id = fields.Many2one('approval.matrix.project.budget', string="Approval Matrix", store=True)
    approval_matrix_project_budget_line_ids = fields.One2many('approval.matrix.project.budget.line',
                                                              'project_budget_id', store=True,
                                                              string="Approved Matrix")
    project_budget_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                    compute='is_project_budget_approval_matrix')
    is_approval_matrix_filled = fields.Boolean(string="Custome Matrix", store=False)
    user_is_approver = fields.Boolean(string='Is Approve Button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.project.budget.line',
                                              string='Project Budget Approval Matrix Line',
                                              store=False)

    approving_matrix_project_budget_id = fields.Many2one('approval.matrix.project.budget', string="Approval Matrix",
                                                         compute='_compute_approving_customer_matrix', store=True)
    project_budget_user_ids = fields.One2many('project.budget.approver.user', 'project_budget_approver_id',
                                              string='Approver')
    approvers_ids = fields.Many2many('res.users', 'project_budget_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    employee_id = fields.Many2one('res.users', string='Users')
    last_approved = fields.Many2one('res.users', string='Users')

    _sql_constraints = [
        ('char_name_uniq', 'unique(char_name)', 'Short Name must be unique')
    ]
    total_material_request = fields.Integer(string='Material Request', compute='_compute_material_request')
    total_purchase_agreement = fields.Integer(string='Purchase Agreement', compute='_compute_purchase_agreement')
    is_recompute_budget = fields.Boolean(string="Is Recompute Budget", compute='_get_is_recompute_budget')
    budget_carry_over_records_count = fields.Integer(compute='_compute_carry_over_count')
    custom_project_progress = fields.Selection(related='project_id.custom_project_progress',)

    @api.depends('project_scope_ids')
    def _get_is_recompute_budget(self):
        for rec in self:
            if rec.project_scope_ids:
                rec.is_recompute_budget = True
            else:
                rec.is_recompute_budget = False

    is_must_refresh = fields.Boolean(string='Must Refresh', default=False, compute='_compute_must_refresh')

    def _compute_must_refresh(self):
        for rec in self:
            is_different = False
            if rec.budget_material_ids:
                if not is_different:
                    for mat in rec.budget_material_ids:
                        if mat.unallocated_quantity != mat.cs_material_id.product_qty_na or mat.unallocated_amount != mat.cs_material_id.product_amt_na:
                            is_different = True
                            break
            if rec.budget_labour_ids:
                if not is_different:
                    for lab in rec.budget_labour_ids:
                        if lab.unallocated_time != lab.cs_labour_id.unallocated_budget_time or lab.unallocated_contractors != lab.cs_labour_id.unallocated_contractors or lab.unallocated_amount != lab.cs_labour_id.product_amt_na:
                            is_different = True
                            break
            if rec.budget_subcon_ids:
                if not is_different:
                    for sub in rec.budget_subcon_ids:
                        if sub.unallocated_quantity != sub.cs_subcon_id.product_qty_na or sub.unallocated_amount != sub.cs_subcon_id.product_amt_na:
                            is_different = True
                            break
            if rec.budget_overhead_ids:
                if not is_different:
                    for ove in rec.budget_overhead_ids:
                        if ove.unallocated_quantity != ove.cs_overhead_id.product_qty_na or ove.unallocated_amount != ove.cs_overhead_id.product_amt_na:
                            is_different = True
                            break
            if rec.budget_equipment_ids:
                if not is_different:
                    for equ in rec.budget_equipment_ids:
                        if equ.unallocated_quantity != equ.cs_equipment_id.product_qty_na or equ.unallocated_amount != equ.cs_equipment_id.product_amt_na:
                            is_different = True
                            break
            if rec.budget_internal_asset_ids:
                if not is_different:
                    for asset in rec.budget_internal_asset_ids:
                        if asset.unallocated_budget_qty != asset.cs_internal_asset_id.unallocated_budget_qty or asset.unallocated_budget_amt != asset.cs_internal_asset_id.unallocated_amt:
                            is_different = True
                            break
            rec.is_must_refresh = is_different

    def _compute_material_request(self):
        for rec in self:
            material_request_count = self.env['material.request'].search_count([('project_budget', '=', rec.id)])
            rec.total_material_request = material_request_count

    def _compute_purchase_agreement(self):
        for rec in self:
            purchase_agreement_count = self.env['purchase.request'].search_count(
                [('project_budget', '=', rec.id), ('is_subcontracting', '=', True)])
            rec.total_purchase_agreement = purchase_agreement_count

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ProjectBudget, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_engineer'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group(
            'abs_construction_management.group_construction_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)

        return res

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))

        return super(ProjectBudget, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))
        return super(ProjectBudget, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                     orderby=orderby, lazy=lazy)

    @api.model
    def create(self, vals):
        project_id = self.env['project.project'].search([('id', '=', vals['project_id'])], limit=1)
        if project_id.budgeting_period:
            vals['name'] = project_id.project_short_name
            if project_id.budgeting_period == 'monthly':
                budget_period_line_id = self.env['budget.period.line'].search([('id', '=', vals['month'])], limit=1)
                if budget_period_line_id:
                    vals['name'] = vals['name'] + '/' + budget_period_line_id.month + '/' + budget_period_line_id.year
            elif project_id.budgeting_period == 'custom':
                # convert datetime.date to string
                start_date = vals['bd_start_date'].strftime("%d-%m-%Y")
                end_date = vals['bd_end_date'].strftime("%d-%m-%Y")
                vals['name'] = vals['name'] + '/' + start_date + '/' + end_date

        return super(ProjectBudget, self).create(vals)

    @api.depends('project_id')
    def is_project_budget_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        project_budget_approval_matrix = IrConfigParam.get_param('is_project_budget_approval_matrix')
        for record in self:
            record.project_budget_approval_matrix = project_budget_approval_matrix

    @api.depends('project_id', 'branch_id', 'company_id', 'department_type', 'analytic_group_id')
    def _compute_approving_customer_matrix(self):
        for res in self:
            res.approving_matrix_project_budget_id = False
            if res.project_budget_approval_matrix:
                if res.department_type == 'project':
                    approving_matrix_project_budget_id = self.env['approval.matrix.project.budget'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('project', 'in', (res.project_id.id)),
                        ('department_type', '=', 'project'),
                        ('set_default', '=', False)], limit=1)

                    approving_matrix_default = self.env['approval.matrix.project.budget'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('set_default', '=', True),
                        ('department_type', '=', 'project')], limit=1)

                else:
                    approving_matrix_project_budget_id = self.env['approval.matrix.project.budget'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('project', 'in', (res.project_id.id)),
                        ('department_type', '=', 'department'),
                        ('set_default', '=', False)], limit=1)

                    approving_matrix_default = self.env['approval.matrix.project.budget'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('set_default', '=', True),
                        ('department_type', '=', 'department')], limit=1)

                if approving_matrix_project_budget_id:
                    res.approving_matrix_project_budget_id = approving_matrix_project_budget_id and approving_matrix_project_budget_id.id or False
                else:
                    if approving_matrix_default:
                        res.approving_matrix_project_budget_id = approving_matrix_default and approving_matrix_default.id or False

    @api.onchange('project_id', 'approving_matrix_project_budget_id', 'analytic_group_id')
    def onchange_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.project_id:
                app_list = []
                if record.state == 'draft' and record.project_budget_approval_matrix:
                    record.project_budget_user_ids = []
                    for rec in record.approving_matrix_project_budget_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'user_ids': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                    record.approvers_ids = app_list
                    record.project_budget_user_ids = data

    def _compute_is_approver(self):
        for record in self:
            if record.approvers_ids:
                current_user = record.env.user
                matrix_line = sorted(record.project_budget_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(record.project_budget_user_ids)
                if app < a:
                    for line in record.project_budget_user_ids[app]:
                        if current_user in line.user_ids:
                            record.is_approver = True
                        else:
                            record.is_approver = False
                else:
                    record.is_approver = False
            else:
                record.is_approver = False

    def request_approval(self):
        if len(self.project_budget_user_ids) == 0:
            raise ValidationError(
                _("There's no periodical budget approval matrix for this project or approval matrix default created. "
                  "You have to create it first."))

        for record in self:
            total_line = (len(record.budget_material_ids) + len(record.budget_labour_ids)
                          + len(record.budget_overhead_ids)
                          + len(record.budget_internal_asset_ids) + len(record.budget_equipment_ids)
                          + len(record.budget_subcon_ids))
            if total_line == 0:
                raise ValidationError(
                    _("There's no budget estimation for this periodical budget. "
                      "You have to add a line first."))

            for mat in record.budget_material_ids:
                for bud in mat.cs_material_id:
                    if mat.quantity > bud.product_qty_na:
                        raise ValidationError("The material quantity is over the unallocated quantity")
            for lab in record.budget_labour_ids:
                for bud in lab.cs_labour_id:
                    # if lab.quantity > bud.product_qty_na:
                    #     raise ValidationError("The labour quantity is over the unallocated quantity")
                    if lab.unallocated_time > bud.unallocated_budget_time:
                        raise ValidationError("The labour time is over the unallocated time")
                    if lab.unallocated_contractors > bud.unallocated_contractors:
                        raise ValidationError("The labour contractors is over the unallocated contractors")
            for sub in record.budget_subcon_ids:
                for bud in sub.cs_subcon_id:
                    if sub.quantity > bud.product_qty_na:
                        raise ValidationError("The subcon quantity is over the unallocated quantity")
            for ove in record.budget_overhead_ids:
                for bud in ove.cs_overhead_id:
                    if ove.quantity > bud.product_qty_na:
                        raise ValidationError("The overhead quantity is over the unallocated quantity")
            for asset in record.budget_internal_asset_ids:
                if asset.budgeted_qty > asset.unallocated_budget_qty:
                    raise ValidationError("The asset quantity is over the unallocated quantity")
            for equ in record.budget_equipment_ids:
                for bud in equ.cs_equipment_id:
                    if equ.quantity > bud.product_qty_na:
                        raise ValidationError("The equipment quantity is over the unallocated quantity")

            action_id = self.env.ref('equip3_construction_operation.project_budget_action')
            template_id = self.env.ref('equip3_construction_operation.email_template_reminder_for_project_budget')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=project.budget'
            if record.project_budget_user_ids and len(record.project_budget_user_ids[0].user_ids) > 1:
                for approved_matrix_id in record.project_budget_user_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from': self.env.user.company_id.email,
                        'email_to': approver.partner_id.email,
                        'approver_name': approver.name,
                        'date': date.today(),
                        'url': url,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
            else:
                approver = record.project_budget_user_ids[0].user_ids[0]
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': approver.partner_id.email,
                    'approver_name': approver.name,
                    'date': date.today(),
                    'url': url,
                }
                template_id.with_context(ctx).send_mail(record.id, True)

            record.write({'employee_id': self.env.user.id,
                          'state': 'to_approve',
                          })

            for line in record.project_budget_user_ids:
                line.write({'approver_state': 'draft'})

    def btn_approve(self):
        sequence_matrix = [data.name for data in self.project_budget_user_ids]
        sequence_approval = [data.name for data in self.project_budget_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.project_budget_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)

        for record in self:
            action_id = self.env.ref('equip3_construction_operation.project_budget_action')
            template_app = self.env.ref('equip3_construction_operation.email_template_project_budget_approved')
            template_id = self.env.ref('equip3_construction_operation.email_template_reminder_for_project_budget_temp')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=project.budget'

            current_user = self.env.uid
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"

            if self.env.user not in record.approved_user_ids:
                if record.is_approver:
                    for line in record.project_budget_user_ids:
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

                    matrix_line = sorted(record.project_budget_user_ids.filtered(lambda r: r.is_approve == False))
                    if len(matrix_line) == 0:
                        record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                        ctx = {
                            'email_from': self.env.user.company_id.email,
                            'email_to': record.employee_id.email,
                            'date': date.today(),
                            'url': url,
                        }
                        template_app.sudo().with_context(ctx).send_mail(record.id, True)
                        record.btn_confirm_project()
                        record.write({'state': 'in_progress'})

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
            action_id = self.env.ref('equip3_construction_operation.project_budget_action')
            template_rej = self.env.ref('equip3_construction_operation.email_template_project_budget_rejected')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=project.budget'
            for user in record.project_budget_user_ids:
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

    def action_material_request(self):
        return {
            'name': "Material Request",
            'view_mode': 'tree,form',
            'res_model': 'material.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_budget', '=', self.id)],
        }

    def action_purchase_agreement(self):
        return {
            'name': "Purchase Agreement",
            'view_mode': 'tree,form',
            'res_model': 'purchase.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_budget', '=', self.id), ('is_subcontracting', '=', True)],
        }

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'approval.matrix.project.budget.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.onchange('project_id')
    def _onchange_project_id_branch(self):
        for rec in self:
            project = rec.project_id
            if project:
                rec.branch_id = project.branch_id.id
            else:
                rec.branch_id = False

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
                                           ('id', 'in', self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'),
                                                  ('primary_states', '=', 'progress'),
                                                  ('company_id', '=', rec.company_id.id),
                                                  ('id', 'in', self.env.user.project_ids.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {
                            'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'),
                                                  ('primary_states', '=', 'progress'),
                                                  ('company_id', '=', rec.company_id.id)]}
                    }

    # ...... newly_added .....
    @api.depends('budget_material_ids.unused_amt')
    def _compute_unused_material(self):
        for sheet in self:
            amount_unused_material = 0.0
            for line in sheet.budget_material_ids:
                amount_unused_material += line.unused_amt
            sheet.update({'amount_unused_material': amount_unused_material})

    # asset
    amount_left_budget = fields.Monetary(string='Budget left', readonly=True, compute='_compute_amount_left_asset')
    amount_total_budget = fields.Monetary(string='Total Cost', readonly=True, compute='_compute_amount_reserved_budget')
    amount_unused_budget = fields.Monetary(string='Budget Unused', readonly=True,
                                           compute='_compute_amount_reserved_budget')
    amount_used_budget = fields.Monetary(string='Budget Used', readonly=True, compute="_compute_amount_reserved_budget")

    @api.depends('budget_internal_asset_ids.budgeted_amt_left')
    def _compute_amount_left_asset(self):
        for sheet in self:
            amount_asset_left = 0.0
            for line in sheet.budget_internal_asset_ids:
                amount_asset_left += line.budgeted_amt_left
            sheet.update({'amount_left_budget': amount_asset_left})

    @api.depends('budget_internal_asset_ids.budgeted_amt', 'budget_internal_asset_ids.budgeted_amt_left',
                 'budget_internal_asset_ids.actual_used_amt')
    def _compute_amount_reserved_budget(self):
        for sheet in self:
            amount_unused_budget = 0.0
            amount_used_budget, amount_reserved_budget = 0, 0
            for line in sheet.budget_internal_asset_ids:
                amount_unused_budget += line.budgeted_amt_left
                amount_used_budget += line.actual_used_amt
                amount_reserved_budget += line.budgeted_amt
            sheet.amount_unused_budget = amount_unused_budget
            sheet.amount_used_budget = amount_used_budget
            sheet.amount_total_budget = amount_reserved_budget

    def _compute_carry_over_count(self):
        for rec in self:
            carry_over = self.env['project.budget.carry'].sudo().search_count([('from_project_budget_id', '=', rec.id)])
            if carry_over:
                rec.budget_carry_over_records_count = carry_over
            else:
                rec.budget_carry_over_records_count = 0

    def budget_carry_over_records(self):
        return {
            'name': _('Budget Carry Over'),
            'view_mode': 'tree,form',
            'res_model': 'project.budget.carry',
            'domain': [('from_project_budget_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }

    # amount internal transfer budget
    @api.depends('history_bt_ids.allocation_amount', 'history_bt_ids.send_amount')
    def _amount_free_project(self):
        for res in self:
            project_amt = 0.0
            receive_amt = 0.0
            send_amt = 0.0
            for line in res.history_bt_ids:
                project_amt += line.allocation_amount
                # send_amt += line.send_amount
            # project_amt = receive_amt - send_amt
            res.amount_from_project = project_amt
            # res.update({'amount_from_project': round(project_amt)})

    @api.depends('history_bt_ids.allocation_amount', 'history_bt_ids.send_amount')
    def _amount_send_project(self):
        for res in self:
            project_amt = 0.0
            receive_amt = 0.0
            send_amt = 0.0
            for line in res.history_bt_ids:
                send_amt += line.send_amount
            res.amount_send_project = send_amt

    @api.depends('history_itb_bud_ids.free_amt')
    def _amount_free_adjusted(self):
        for res in self:
            freea = 0.00
            freeb = 0.00
            for line in res.itb_line_bud_ids:
                freea += line.adjusted
            for line in res.budget_transfer_line_ids:
                freeb += line.adjusted
            res.amount_from_adjusted = (freea + freeb) * -1

    # @api.depends('amount_from_adjusted', 'amount_from_project')
    # def _amount_free(self):
    #     for res in self:
    #         free_amt = 0.00
    #         free_amt = res.total_period_budget - res.budget_amount_total
    #         res.amount_free = free_amt

    def create_budget_carry_over(self):
        return {
            'name': _('Budget Carry Over'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.budget.carry.over',
            'target': 'new',
            'context': {'default_id': self.id,
                        'default_project_id': self.project_id.id,
                        'default_budget_default_id': self.id},
        }

    def create_budget_transfer(self):
        for record in self:
            context = {
                'default_is_budget_transfer': True,
                'default_project_id': record.project_id.id,
                'default_branch_id': record.branch_id.id,
                'default_project_budget': record.id,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Change Budget Request',
                'view_mode': 'form',
                'res_model': 'internal.transfer.budget',
                'context': context,
            }

    def create_change_allocation_request(self):
        for rec in self:
            context = {
                'default_project_id': rec.project_id.id,
                'default_project_budget': rec.id,
                'default_branch_id': rec.branch_id.id,
                'default_is_project_transfer': False,
                'default_is_change_allocation': True,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Change Allocation Budget',
                'view_mode': 'form',
                'res_model': 'internal.transfer.budget',
                'context': context,
                'target': 'current',
            }

    def create_budget_bud_change_request(self):
        for record in self:
            context = {
                'default_project_id': record.project_id.id,
                'default_branch_id': record.branch_id.id,
                'default_project_budget': record.id,
                'default_is_project_transfer': False,
                'default_is_change_allocation': False,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Budget Change Request',
                'view_mode': 'form',
                'res_model': 'internal.transfer.budget',
                'context': context,
                'target': 'current',
            }

    # --------- freeze/unfreeze in 'project budget' --------
    def ba_proj_budget_freeze(self):
        return self.write({'state': 'freeze'})

    def ba_proj_budget_unfreeze(self):
        return self.write({'state': 'in_progress'})

    # def _compute_name(self):
    #     for rec in self:
    #         name = ''
    #         if rec.cost_sheet and rec.month and rec.period:
    #             name = rec.cost_sheet.cost_sheet_name + ' - ' + rec.month.month + ' - ' + rec.period.name
    #         else:
    #             name = rec.char_name
    #         rec.name = name
    #         # rec.write({'name': record})
    #         # rec.write({'name': record})

    @api.depends('budget_material_ids.amt_res', 'budget_material_gop_ids.amt_res')
    def _compute_amount_reserved_material(self):
        for sheet in self:
            amount_material_reserved = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_material_gop_ids:
                    amount_material_reserved += line.amt_res
            else:
                for line in sheet.budget_material_ids:
                    amount_material_reserved += line.amt_res
            sheet.update({'amount_reserved_material': amount_material_reserved})

    @api.depends('budget_material_ids.purchased_amt', 'budget_material_gop_ids.purchased_amt')
    def _compute_amount_purchased_material(self):
        for sheet in self:
            amount_material_purchased = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_material_gop_ids:
                    amount_material_purchased += line.purchased_amt
            else:
                for line in sheet.budget_material_ids:
                    amount_material_purchased += line.purchased_amt
            sheet.update({'amount_purchased_material': amount_material_purchased})

    @api.depends('budget_material_ids.transferred_amt', 'budget_material_gop_ids.transferred_amt')
    def _compute_amount_transferred_material(self):
        for sheet in self:
            amount_material_transferred = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_material_gop_ids:
                    amount_material_transferred += line.transferred_amt
            else:
                for line in sheet.budget_material_ids:
                    amount_material_transferred += line.transferred_amt
            sheet.update({'amount_transferred_material': amount_material_transferred})

    @api.depends('budget_material_ids.amt_used', 'budget_material_gop_ids.amt_used')
    def _compute_amount_used_material(self):
        for sheet in self:
            amount_material_used = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_material_gop_ids:
                    amount_material_used += line.amt_used
            else:
                for line in sheet.budget_material_ids:
                    amount_material_used += line.amt_used
            sheet.update({'amount_used_material': amount_material_used})

    @api.depends('budget_material_ids.amt_left', 'budget_material_gop_ids.amt_left')
    def _compute_amount_left_material(self):
        for sheet in self:
            amount_material_left = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_material_gop_ids:
                    amount_material_left += line.amt_left
            else:
                for line in sheet.budget_material_ids:
                    amount_material_left += line.amt_left
            sheet.update({'amount_left_material': amount_material_left})

    @api.depends('budget_material_ids.amount_total', 'budget_material_gop_ids.amount_total')
    def _compute_amount_material(self):
        for sheet in self:
            amount_material = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_material_gop_ids:
                    amount_material += line.amount_total
            else:
                for line in sheet.budget_material_ids:
                    amount_material += line.amount_total
            sheet.update({'amount_material': amount_material})

    amount_reserved_labour = fields.Monetary(compute='_compute_amount_reserved_labour', string='Labour Budget Reserved',
                                             readonly=True)
    amount_purchased_labour = fields.Monetary(compute='_compute_amount_purchased_labour',
                                              string='Labour Budget Purchased', readonly=True)
    amount_transferred_labour = fields.Monetary(compute='_compute_amount_transferred_labour',
                                                string='Labour Budget Transferred', readonly=True)
    amount_used_labour = fields.Monetary(compute='_compute_amount_used_labour', string='Labour Budget Used',
                                         readonly=True)
    amount_left_labour = fields.Monetary(compute='_compute_amount_left_labour', string='Labour Budget Left',
                                         readonly=True)
    amount_labour = fields.Monetary(compute='_compute_amount_labour', string='Labour Cost', readonly=True)
    amount_unused_labour = fields.Monetary(compute='_compute_unused_labour', string='Labour Unused', readonly=True)

    @api.depends('budget_labour_ids.unused_amt', 'budget_labour_gop_ids.unused_amt')
    def _compute_unused_labour(self):
        for sheet in self:
            amount_unused_labour = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_labour_gop_ids:
                    amount_unused_labour += line.unused_amt
            else:
                for line in sheet.budget_labour_ids:
                    amount_unused_labour += line.unused_amt
            sheet.update({'amount_unused_labour': amount_unused_labour})

    @api.depends('budget_labour_ids.amt_res', 'budget_labour_gop_ids.amt_res')
    def _compute_amount_reserved_labour(self):
        for sheet in self:
            amount_labour_reserved = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_labour_gop_ids:
                    amount_labour_reserved += line.amt_res
            else:
                for line in sheet.budget_labour_ids:
                    amount_labour_reserved += line.amt_res
            sheet.update({'amount_reserved_labour': amount_labour_reserved})

    @api.depends('budget_labour_ids.purchased_amt', 'budget_labour_gop_ids.purchased_amt')
    def _compute_amount_purchased_labour(self):
        for sheet in self:
            amount_labour_purchased = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_labour_gop_ids:
                    amount_labour_purchased += line.purchased_amt
            else:
                for line in sheet.budget_labour_ids:
                    amount_labour_purchased += line.purchased_amt
            sheet.update({'amount_purchased_labour': amount_labour_purchased})

    @api.depends('budget_labour_ids.transferred_amt', 'budget_labour_gop_ids.transferred_amt')
    def _compute_amount_transferred_labour(self):
        for sheet in self:
            amount_labour_transferred = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_labour_gop_ids:
                    amount_labour_transferred += line.transferred_amt
            else:
                for line in sheet.budget_labour_ids:
                    amount_labour_transferred += line.transferred_amt
            sheet.update({'amount_transferred_labour': amount_labour_transferred})

    @api.depends('budget_labour_ids.amt_used', 'budget_labour_gop_ids.amt_used')
    def _compute_amount_used_labour(self):
        for sheet in self:
            amount_labour_used = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_labour_gop_ids:
                    amount_labour_used += line.amt_used
            else:
                for line in sheet.budget_labour_ids:
                    amount_labour_used += line.amt_used
            sheet.update({'amount_used_labour': amount_labour_used})

    @api.depends('budget_labour_ids.amt_left', 'budget_labour_gop_ids.amt_left')
    def _compute_amount_left_labour(self):
        for sheet in self:
            amount_labour_left = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_labour_gop_ids:
                    amount_labour_left += line.amt_left
            else:
                for line in sheet.budget_labour_ids:
                    amount_labour_left += line.amt_left
            sheet.update({'amount_left_labour': amount_labour_left})

    @api.depends('budget_labour_ids.amount_total', 'budget_labour_gop_ids.amount_total')
    def _compute_amount_labour(self):
        for sheet in self:
            amount_labour = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_labour_gop_ids:
                    amount_labour += line.amount_total
            else:
                for line in sheet.budget_labour_ids:
                    amount_labour += line.amount_total
            sheet.update({'amount_labour': amount_labour})

    amount_reserved_subcon = fields.Monetary(compute='_compute_amount_reserved_subcon', string='Subcon Budget Reserved',
                                             readonly=True)
    amount_purchased_subcon = fields.Monetary(compute='_compute_amount_purchased_subcon',
                                              string='Subcon Budget Purchased', readonly=True)
    amount_used_subcon = fields.Monetary(compute='_compute_amount_used_subcon', string='Subcon Budget Used',
                                         readonly=True)
    amount_left_subcon = fields.Monetary(compute='_compute_amount_left_subcon', string='Subcon Budget Left',
                                         readonly=True)
    amount_subcon = fields.Monetary(compute='_compute_amount_subcon', string='Subcon Cost', readonly=True)
    amount_unused_subcon = fields.Monetary(compute='_compute_unused_subcon', string='Subcon Unused', readonly=True)

    @api.depends('budget_subcon_ids.unused_amt')
    def _compute_unused_subcon(self):
        for sheet in self:
            amount_unused_subcon = 0.0
            for line in sheet.budget_subcon_ids:
                amount_unused_subcon += line.unused_amt
            sheet.update({'amount_unused_subcon': amount_unused_subcon})

    @api.depends('budget_subcon_ids.amt_res')
    def _compute_amount_reserved_subcon(self):
        for sheet in self:
            amount_subcon_reserved = 0.0
            for line in sheet.budget_subcon_ids:
                amount_subcon_reserved += line.amt_res
            sheet.update({'amount_reserved_subcon': amount_subcon_reserved})

    @api.depends('budget_subcon_ids.purchased_amt')
    def _compute_amount_purchased_subcon(self):
        for sheet in self:
            amount_subcon_purchased = 0.0
            for line in sheet.budget_subcon_ids:
                amount_subcon_purchased += line.purchased_amt
            sheet.update({'amount_purchased_subcon': amount_subcon_purchased})

    @api.depends('budget_subcon_ids.amt_used')
    def _compute_amount_used_subcon(self):
        for sheet in self:
            amount_subcon_used = 0.0
            for line in sheet.budget_subcon_ids:
                amount_subcon_used += line.amt_used
            sheet.update({'amount_used_subcon': amount_subcon_used})

    @api.depends('budget_subcon_ids.amt_left')
    def _compute_amount_left_subcon(self):
        for sheet in self:
            amount_subcon_left = 0.0
            for line in sheet.budget_subcon_ids:
                amount_subcon_left += line.amt_left
            sheet.update({'amount_left_subcon': amount_subcon_left})

    @api.depends('budget_subcon_ids.amount_total')
    def _compute_amount_subcon(self):
        for sheet in self:
            amount_subcon = 0.0
            for line in sheet.budget_subcon_ids:
                amount_subcon += line.amount_total
            sheet.update({'amount_subcon': amount_subcon})

    amount_reserved_overhead = fields.Monetary(compute='_compute_amount_reserved_overhead',
                                               string='Overhead Budget Reserved', readonly=True)
    amount_purchased_overhead = fields.Monetary(compute='_compute_amount_purchased_overhead',
                                                string='Overhead Budget Purchased', readonly=True)
    amount_transferred_overhead = fields.Monetary(compute='_compute_amount_transferred_overhead',
                                                  string='Overhead Budget Transferred', readonly=True)
    amount_used_overhead = fields.Monetary(compute='_compute_amount_used_overhead', string='Overhead Budget Used',
                                           readonly=True)
    amount_left_overhead = fields.Monetary(compute='_compute_amount_left_overhead', string='Overhead Budget Left',
                                           readonly=True)
    amount_overhead = fields.Monetary(compute='_compute_amount_overhead', string='Overhead Cost', readonly=True)
    amount_unused_overhead = fields.Monetary(compute='_compute_unused_reserved_overhead', string=' Overhead Unused',
                                             readonly=True)

    @api.depends('budget_overhead_ids.unused_amt', 'budget_overhead_gop_ids.unused_amt')
    def _compute_unused_reserved_overhead(self):
        for sheet in self:
            amount_unused_overhead = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_overhead_gop_ids:
                    amount_unused_overhead += line.unused_amt
            else:
                for line in sheet.budget_overhead_ids:
                    amount_unused_overhead += line.unused_amt
            sheet.update({'amount_unused_overhead': amount_unused_overhead})

    @api.depends('budget_overhead_ids.amt_res', 'budget_overhead_gop_ids.amt_res')
    def _compute_amount_reserved_overhead(self):
        for sheet in self:
            amount_overhead_reserved = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_overhead_gop_ids:
                    amount_overhead_reserved += line.amt_res
            else:
                for line in sheet.budget_overhead_ids:
                    amount_overhead_reserved += line.amt_res
            sheet.update({'amount_reserved_overhead': amount_overhead_reserved})

    @api.depends('budget_overhead_ids.purchased_amt', 'budget_overhead_gop_ids.purchased_amt')
    def _compute_amount_purchased_overhead(self):
        for sheet in self:
            amount_overhead_purchased = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_overhead_gop_ids:
                    amount_overhead_purchased += line.purchased_amt
            else:
                for line in sheet.budget_overhead_ids:
                    amount_overhead_purchased += line.purchased_amt
            sheet.update({'amount_purchased_overhead': amount_overhead_purchased})

    @api.depends('budget_overhead_ids.transferred_amt', 'budget_overhead_gop_ids.transferred_amt')
    def _compute_amount_transferred_overhead(self):
        for sheet in self:
            amount_overhead_transferred = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_overhead_gop_ids:
                    amount_overhead_transferred += line.transferred_amt
            else:
                for line in sheet.budget_overhead_ids:
                    amount_overhead_transferred += line.transferred_amt
            sheet.update({'amount_transferred_overhead': amount_overhead_transferred})

    @api.depends('budget_overhead_ids.amt_used', 'budget_overhead_gop_ids.amt_used')
    def _compute_amount_used_overhead(self):
        for sheet in self:
            amount_overhead_used = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_overhead_gop_ids:
                    amount_overhead_used += line.amt_used
            else:
                for line in sheet.budget_overhead_ids:
                    amount_overhead_used += line.amt_used
            sheet.update({'amount_used_overhead': amount_overhead_used})

    @api.depends('budget_overhead_ids.amt_left', 'budget_overhead_gop_ids.amt_left')
    def _compute_amount_left_overhead(self):
        for sheet in self:
            amount_overhead_left = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_overhead_gop_ids:
                    amount_overhead_left += line.amt_left
            else:
                for line in sheet.budget_overhead_ids:
                    amount_overhead_left += line.amt_left
            sheet.update({'amount_left_overhead': amount_overhead_left})

    @api.depends('budget_overhead_ids.amount_total', 'budget_overhead_gop_ids.amount_total')
    def _compute_amount_overhead(self):
        for sheet in self:
            amount_overhead = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_overhead_gop_ids:
                    amount_overhead += line.amount_total
            else:
                for line in sheet.budget_overhead_ids:
                    amount_overhead += line.amount_total
            sheet.update({'amount_overhead': amount_overhead})

    amount_reserved_equipment = fields.Monetary(compute='_compute_amount_reserved_equipment',
                                                string='Equipment Budget Reserved', readonly=True)
    amount_purchased_equipment = fields.Monetary(compute='_compute_amount_purchased_equipment',
                                                 string='Equipment Budget Purchased', readonly=True)
    amount_used_equipment = fields.Monetary(compute='_compute_amount_used_equipment', string='Equipment Budget Used',
                                            readonly=True)
    amount_left_equipment = fields.Monetary(compute='_compute_amount_left_equipment', string='Equipment Budget Left',
                                            readonly=True)
    amount_equipment = fields.Monetary(compute='_compute_amount_equipment', string='Equipment Cost', readonly=True)
    amount_unused_equipment = fields.Monetary(compute='_compute_unused_reserved_equipment', string='Equipment Unused',
                                              readonly=True)

    @api.depends('budget_equipment_ids.unused_amt', 'budget_equipment_gop_ids.unused_amt')
    def _compute_unused_reserved_equipment(self):
        for sheet in self:
            amount_unused_equipment = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_equipment_gop_ids:
                    amount_unused_equipment += line.unused_amt
            else:
                for line in sheet.budget_equipment_ids:
                    amount_unused_equipment += line.unused_amt
            sheet.update({'amount_unused_equipment': amount_unused_equipment})

    @api.depends('budget_equipment_ids.amt_res', 'budget_equipment_gop_ids.amt_res')
    def _compute_amount_reserved_equipment(self):
        for sheet in self:
            amount_equipment_reserved = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_equipment_gop_ids:
                    amount_equipment_reserved += line.amt_res
            else:
                for line in sheet.budget_equipment_ids:
                    amount_equipment_reserved += line.amt_res
            sheet.update({'amount_reserved_equipment': amount_equipment_reserved})

    @api.depends('budget_equipment_ids.purchased_amt', 'budget_equipment_gop_ids.purchased_amt')
    def _compute_amount_purchased_equipment(self):
        for sheet in self:
            amount_equipment_purchased = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_equipment_gop_ids:
                    amount_equipment_purchased += line.purchased_amt
            else:
                for line in sheet.budget_equipment_ids:
                    amount_equipment_purchased += line.purchased_amt
            sheet.update({'amount_purchased_equipment': amount_equipment_purchased})

    @api.depends('budget_equipment_ids.amt_used', 'budget_equipment_gop_ids.amt_used')
    def _compute_amount_used_equipment(self):
        for sheet in self:
            amount_equipment_used = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_equipment_gop_ids:
                    amount_equipment_used += line.amt_used
            else:
                for line in sheet.budget_equipment_ids:
                    amount_equipment_used += line.amt_used
            sheet.update({'amount_used_equipment': amount_equipment_used})

    @api.depends('budget_equipment_ids.amt_left', 'budget_equipment_gop_ids.amt_left')
    def _compute_amount_left_equipment(self):
        for sheet in self:
            amount_equipment_left = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_equipment_gop_ids:
                    amount_equipment_left += line.amt_left
            else:
                for line in sheet.budget_equipment_ids:
                    amount_equipment_left += line.amt_left
            sheet.update({'amount_left_equipment': amount_equipment_left})

    @api.depends('budget_equipment_ids.amount_total', 'budget_equipment_gop_ids.amount_total')
    def _compute_amount_equipment(self):
        for sheet in self:
            amount_equipment = 0.0
            if sheet.budgeting_method == 'gop_budget':
                for line in sheet.budget_equipment_gop_ids:
                    amount_equipment += line.amount_total
            else:
                for line in sheet.budget_equipment_ids:
                    amount_equipment += line.amount_total
            sheet.update({'amount_equipment': amount_equipment})

    def _compute_currency(self):
        self.currency_id = self.company_id.currency_id

    budget_material_gop_ids = fields.One2many('budget.gop.material', 'budget_id')
    budget_labour_gop_ids = fields.One2many('budget.gop.labour', 'budget_id')
    budget_overhead_gop_ids = fields.One2many('budget.gop.overhead', 'budget_id')
    budget_equipment_gop_ids = fields.One2many('budget.gop.equipment', 'budget_id')

    # budget actual
    budget_res = fields.Monetary(string='Total Budget Reserved', readonly=True, Store=True, force_save="1",
                                 compute='_amount_budget_actual')
    budget_pur = fields.Monetary(string='Total Budget Purchased', readonly=True, Store=True, force_save="1",
                                 compute='_amount_budget_actual')
    budget_tra = fields.Monetary(string='Total Budget Transferred', readonly=True, Store=True, force_save="1",
                                 compute='_amount_budget_actual')
    budget_left = fields.Monetary(string='Total Budget Left', readonly=True, Store=True, force_save="1",
                                  compute='_amount_budget_actual')
    budget_unused = fields.Monetary(string='Total Budget Unused', readonly=True, Store=True,
                                    compute='_amount_budget_actual')
    budget_used = fields.Monetary(string='Total Budget Used', readonly=True, Store=True,
                                  compute='_amount_budget_actual')

    @api.depends('amount_reserved_material', 'amount_purchased_material', 'amount_transferred_material',
                 'amount_used_material', 'amount_unused_material', 'amount_left_material',
                 'amount_reserved_labour', 'amount_purchased_labour', 'amount_transferred_labour', 'amount_used_labour',
                 'amount_unused_labour', 'amount_left_labour',
                 'amount_reserved_subcon', 'amount_purchased_subcon', 'amount_used_subcon', 'amount_unused_subcon',
                 'amount_left_subcon',
                 'amount_reserved_overhead', 'amount_purchased_overhead', 'amount_transferred_overhead',
                 'amount_used_overhead', 'amount_unused_overhead', 'amount_left_overhead',
                 'amount_reserved_equipment', 'amount_purchased_equipment', 'amount_used_equipment',
                 'amount_unused_equipment', 'amount_left_equipment',
                 'amount_left_budget', 'amount_used_budget', 'amount_unused_budget')
    def _amount_budget_actual(self):
        for budget in self:
            reserved_budget = 0.00
            purchased_budget = 0.00
            transferred_budget = 0.00
            left_budget = 0.00
            unused_budget = 0.00
            used_budget = 0.00
            reserved_budget = budget.amount_reserved_material + budget.amount_reserved_labour + budget.amount_reserved_subcon + budget.amount_reserved_overhead + budget.amount_reserved_equipment
            purchased_budget = budget.amount_purchased_material + budget.amount_purchased_labour + budget.amount_purchased_subcon + budget.amount_purchased_overhead + budget.amount_purchased_equipment
            transferred_budget = budget.amount_transferred_material + budget.amount_transferred_labour + budget.amount_transferred_overhead
            left_budget = budget.amount_left_material + budget.amount_left_labour + budget.amount_left_subcon + budget.amount_left_overhead + budget.amount_left_equipment + budget.amount_left_budget
            unused_budget = budget.amount_unused_material + budget.amount_unused_labour + budget.amount_unused_subcon + budget.amount_unused_overhead + budget.amount_unused_equipment + budget.amount_unused_budget
            used_budget = budget.amount_used_material + budget.amount_used_labour + budget.amount_used_subcon + budget.amount_used_overhead + budget.amount_used_equipment + budget.amount_used_budget
            budget.update({
                'budget_res': reserved_budget,
                'budget_pur': purchased_budget,
                'budget_tra': transferred_budget,
                'budget_left': left_budget,
                'budget_unused': unused_budget,
                'budget_used': used_budget,
            })

    @api.depends('budgeting_method', 'budget_material_ids.amount_total', 'budget_labour_ids.amount_total',
                 'budget_overhead_ids.amount_total', 'budget_subcon_ids.amount_total',
                 'budget_equipment_ids.amount_total',
                 'budget_internal_asset_ids.budgeted_amt', 'budget_material_gop_ids.amount_total',
                 'budget_labour_gop_ids.amount_total',
                 'budget_overhead_gop_ids.amount_total', 'budget_equipment_gop_ids.amount_total')
    def _amount_total(self):
        for res in self:
            amount_material = 0.0
            amount_labour = 0.0
            amount_overhead = 0.0
            amount_subcon = 0.0
            amount_equipment = 0.0
            amount_asset = 0.0
            amount = 0.0
            if res.budgeting_method == 'gop_budget':
                for line in res.budget_material_gop_ids:
                    amount_material += line.amount_total

                for line in res.budget_labour_gop_ids:
                    amount_labour += line.amount_total

                for line in res.budget_overhead_gop_ids:
                    amount_overhead += line.amount_total

                for line in res.budget_equipment_gop_ids:
                    amount_equipment += line.amount_total

            else:
                for line in res.budget_material_ids:
                    amount_material += line.amount_total

                for line in res.budget_labour_ids:
                    amount_labour += line.amount_total

                for line in res.budget_overhead_ids:
                    amount_overhead += line.amount_total

                for line in res.budget_equipment_ids:
                    amount_equipment += line.amount_total

            for line in res.budget_internal_asset_ids:
                amount_asset += line.budgeted_amt

            for line in res.budget_subcon_ids:
                amount_subcon += line.amount_total

            amount = (
                    amount_material + amount_labour + amount_subcon + amount_overhead + amount_equipment + amount_asset)
            res.budget_amount_total = amount

    @api.depends('budget_material_ids.amt_used', 'budget_labour_ids.amt_used',
                 'budget_overhead_ids.amt_used', 'budget_subcon_ids.amt_used',
                 'budget_equipment_ids.amt_used', )
    def _act_amount_total(self):
        for res in self:
            amount_material = 0.0
            amount_labour = 0.0
            amount_overhead = 0.0
            amount_subcon = 0.0
            amount_equipment = 0.0
            amount_asset = 0.0

            for line in res.budget_material_ids:
                amount_material += line.amt_used

            for line in res.budget_labour_ids:
                amount_labour += line.amt_used

            for line in res.budget_subcon_ids:
                amount_subcon += line.amt_used

            for line in res.budget_overhead_ids:
                amount_overhead += line.amt_used

            for line in res.budget_equipment_ids:
                amount_equipment += line.amt_used

            for line in res.budget_internal_asset_ids:
                amount_asset += line.actual_used_amt
            self.actual_amount_total = (
                    amount_material + amount_labour + amount_subcon + amount_overhead + amount_equipment + amount_asset)

    @api.depends('budget_material_ids.purchased_amt', 'budget_labour_ids.purchased_amt',
                 'budget_overhead_ids.purchased_amt', 'budget_subcon_ids.purchased_amt',
                 'budget_equipment_ids.purchased_amt')
    def _pur_amount_total(self):
        for res in self:
            amount_material = 0.0
            amount_labour = 0.0
            amount_overhead = 0.0
            amount_subcon = 0.0
            amount_equipment = 0.0
            for line in res.budget_material_ids:
                amount_material += line.purchased_amt

            for line in res.budget_labour_ids:
                amount_labour += line.purchased_amt

            for line in res.budget_subcon_ids:
                amount_subcon += line.purchased_amt

            for line in res.budget_overhead_ids:
                amount_overhead += line.purchased_amt

            for line in res.budget_equipment_ids:
                amount_equipment += line.purchased_amt
            self.purchased_amount_total = (
                    amount_material + amount_labour + amount_subcon + amount_overhead + amount_equipment)

    @api.depends('budget_material_ids.transferred_amt', 'budget_labour_ids.transferred_amt',
                 'budget_overhead_ids.transferred_amt')
    def _tra_amount_total(self):
        for res in self:
            amount_material = 0.0
            amount_labour = 0.0
            amount_overhead = 0.0
            for line in res.budget_material_ids:
                amount_material += line.transferred_amt

            for line in res.budget_labour_ids:
                amount_labour += line.transferred_amt

            for line in res.budget_overhead_ids:
                amount_overhead += line.transferred_amt
            # self.actual_amount_total = (amount_material + amount_labour + amount_overhead)

    @api.constrains('month')
    def _check_existing_record(self):
        for record in self:
            if record.budgeting_period == 'monthly':
                month_id = self.env['project.budget'].search(
                    [('project_id', '=', record.project_id.id), ('month', '=', record.month.id),
                     ('state', 'not in', ('cancelled', 'rejected'))])
                if len(month_id) > 1:
                    raise ValidationError(
                        f'The project budget for this month is already created. Please change the month')
            elif record.budgeting_period == 'custom':
                month_id = self.env['project.budget'].search(
                    [('project_id', '=', record.project_id.id),
                     ('state', 'not in', ('cancelled', 'rejected')),
                     '|', '|',
                     '&', ('bd_start_date', '<=', record.bd_start_date), ('bd_end_date', '>=', record.bd_start_date),
                     '&', ('bd_start_date', '<=', record.bd_end_date), ('bd_end_date', '>=', record.bd_end_date),
                     '&', ('bd_start_date', '>=', record.bd_start_date), ('bd_end_date', '<=', record.bd_end_date)])
                if len(month_id) > 1:
                    raise ValidationError(
                        f'The project budget for the date is already created. Please change the date')
            else:
                month_id = self.env['project.budget'].search(
                    [('project_id', '=', record.project_id.id)])
                if len(month_id) > 1:
                    raise ValidationError(
                        f'The project budget for this project already created')

    @api.onchange('budget_material_ids')
    def get_gop_material_table(self):
        self.budget_material_gop_ids = [(5, 0, 0)]
        gop_budget_dict = {}
        for item in self.budget_material_ids:
            # key_gop_budget = project_scope + section_name + group_of_product
            key_gop_budget = str(item.project_scope.id) + str(item.section_name.id) + str(item.group_of_product.id)
            if gop_budget_dict.get(key_gop_budget, False):
                gop_budget_dict[key_gop_budget]['amount_total'] += item.amount_total
                gop_budget_dict[key_gop_budget]['budget_amount'] += item.budget_amount
                gop_budget_dict[key_gop_budget]['carried_amt'] += item.carried_amt
                gop_budget_dict[key_gop_budget]['carry_amt'] += item.carry_amt
                gop_budget_dict[key_gop_budget]['amt_res'] += item.amt_res
                gop_budget_dict[key_gop_budget]['billed_amt'] += item.billed_amt
                gop_budget_dict[key_gop_budget]['purchased_amt'] += item.purchased_amt
                gop_budget_dict[key_gop_budget]['transferred_amt'] += item.transferred_amt
                gop_budget_dict[key_gop_budget]['dif_amt_used'] += item.dif_amt_used
                gop_budget_dict[key_gop_budget]['amt_used'] += item.amt_used
                gop_budget_dict[key_gop_budget]['amount_return'] += item.amount_return
            else:
                gop_budget_dict[key_gop_budget] = {
                    'cs_material_gop_id': item.cs_material_id.material_gop_id.id,
                    'project_scope': item.project_scope.id,
                    'section_name': item.section_name.id,
                    'group_of_product': item.group_of_product.id,
                    'amount_total': item.amount_total,
                    'unallocated_amount': item.cs_material_id.material_gop_id.product_amt_na,
                    'budget_amount': item.budget_amount,
                    'carried_amt': item.carried_amt,
                    'carry_amt': item.carry_amt,
                    'amt_res': item.amt_res,
                    'billed_amt': item.billed_amt,
                    'purchased_amt': item.purchased_amt,
                    'transferred_amt': item.transferred_amt,
                    'dif_amt_used': item.dif_amt_used,
                    'amt_used': item.amt_used,
                    'amount_return': item.amount_return,
                }
            # if gop_budget_dict[key_gop_budget]['amount_total'] > gop_budget_dict[key_gop_budget]['unallocated_amount']:
            #     raise ValidationError('Budget amount is greater than unallocated amount')

        self.budget_material_gop_ids = [(0, 0, item) for k, item in gop_budget_dict.items()]

    @api.onchange('budget_labour_ids')
    def get_gop_labour_table(self):
        self.budget_labour_gop_ids = [(5, 0, 0)]
        gop_budget_dict = {}
        for item in self.budget_labour_ids:
            # item._amount_total_comute()
            # key_gop_budget = project_scope + section_name + group_of_product
            key_gop_budget = str(item.project_scope.id) + str(item.section_name.id) + str(item.group_of_product.id)
            if gop_budget_dict.get(key_gop_budget, False):
                gop_budget_dict[key_gop_budget]['amount_total'] += item.amount_total
                gop_budget_dict[key_gop_budget]['budget_amount'] += item.budget_amount
                gop_budget_dict[key_gop_budget]['carried_amt'] += item.carried_amt
                gop_budget_dict[key_gop_budget]['carry_amt'] += item.carry_amt
                gop_budget_dict[key_gop_budget]['amt_res'] += item.amt_res
                gop_budget_dict[key_gop_budget]['billed_amt'] += item.billed_amt
                gop_budget_dict[key_gop_budget]['purchased_amt'] += item.purchased_amt
                gop_budget_dict[key_gop_budget]['transferred_amt'] += item.transferred_amt
                gop_budget_dict[key_gop_budget]['dif_amt_used'] += item.dif_amt_used
                gop_budget_dict[key_gop_budget]['amt_used'] += item.amt_used
                gop_budget_dict[key_gop_budget]['amount_return'] += item.amount_return
            else:
                gop_budget_dict[key_gop_budget] = {
                    'cs_labour_gop_id': item.cs_labour_id.labour_gop_id.id,
                    'project_scope': item.project_scope.id,
                    'section_name': item.section_name.id,
                    'group_of_product': item.group_of_product.id,
                    'amount_total': item.amount_total,
                    'unallocated_amount': item.cs_labour_id.labour_gop_id.product_amt_na,
                    'budget_amount': item.budget_amount,
                    'carried_amt': item.carried_amt,
                    'carry_amt': item.carry_amt,
                    'amt_res': item.amt_res,
                    'billed_amt': item.billed_amt,
                    'purchased_amt': item.purchased_amt,
                    'transferred_amt': item.transferred_amt,
                    'dif_amt_used': item.dif_amt_used,
                    'amt_used': item.amt_used,
                    'amount_return': item.amount_return,
                }

        self.budget_labour_gop_ids = [(0, 0, item) for k, item in gop_budget_dict.items()]

    @api.onchange('budget_overhead_ids')
    def get_gop_overhead_table(self):
        self.budget_overhead_gop_ids = [(5, 0, 0)]
        gop_budget_dict = {}
        for item in self.budget_overhead_ids:
            # key_gop_budget = project_scope + section_name + group_of_product
            key_gop_budget = str(item.project_scope.id) + str(item.section_name.id) + str(item.group_of_product.id)
            if gop_budget_dict.get(key_gop_budget, False):
                gop_budget_dict[key_gop_budget]['amount_total'] += item.amount_total
                gop_budget_dict[key_gop_budget]['budget_amount'] += item.budget_amount
                gop_budget_dict[key_gop_budget]['carried_amt'] += item.carried_amt
                gop_budget_dict[key_gop_budget]['carry_amt'] += item.carry_amt
                gop_budget_dict[key_gop_budget]['amt_res'] += item.amt_res
                gop_budget_dict[key_gop_budget]['billed_amt'] += item.billed_amt
                gop_budget_dict[key_gop_budget]['purchased_amt'] += item.purchased_amt
                gop_budget_dict[key_gop_budget]['transferred_amt'] += item.transferred_amt
                gop_budget_dict[key_gop_budget]['dif_amt_used'] += item.dif_amt_used
                gop_budget_dict[key_gop_budget]['amt_used'] += item.amt_used
                gop_budget_dict[key_gop_budget]['amount_return'] += item.amount_return
            else:
                gop_budget_dict[key_gop_budget] = {
                    'cs_overhead_gop_id': item.cs_overhead_id.overhead_gop_id.id,
                    'project_scope': item.project_scope.id,
                    'section_name': item.section_name.id,
                    'group_of_product': item.group_of_product.id,
                    'amount_total': item.amount_total,
                    'unallocated_amount': item.cs_overhead_id.overhead_gop_id.product_amt_na,
                    'budget_amount': item.budget_amount,
                    'carried_amt': item.carried_amt,
                    'carry_amt': item.carry_amt,
                    'amt_res': item.amt_res,
                    'billed_amt': item.billed_amt,
                    'purchased_amt': item.purchased_amt,
                    'transferred_amt': item.transferred_amt,
                    'dif_amt_used': item.dif_amt_used,
                    'amt_used': item.amt_used,
                    'amount_return': item.amount_return,
                }

        self.budget_overhead_gop_ids = [(0, 0, item) for k, item in gop_budget_dict.items()]

    @api.onchange('budget_equipment_ids')
    def get_gop_equipment_table(self):
        self.budget_equipment_gop_ids = [(5, 0, 0)]
        gop_budget_dict = {}
        for item in self.budget_equipment_ids:
            # key_gop_budget = project_scope + section_name + group_of_product
            key_gop_budget = str(item.project_scope.id) + str(item.section_name.id) + str(item.group_of_product.id)
            if gop_budget_dict.get(key_gop_budget, False):
                gop_budget_dict[key_gop_budget]['amount_total'] += item.amount_total
                gop_budget_dict[key_gop_budget]['budget_amount'] += item.budget_amount
                gop_budget_dict[key_gop_budget]['carried_amt'] += item.carried_amt
                gop_budget_dict[key_gop_budget]['carry_amt'] += item.carry_amt
                gop_budget_dict[key_gop_budget]['amt_res'] += item.amt_res
                gop_budget_dict[key_gop_budget]['billed_amt'] += item.billed_amt
                gop_budget_dict[key_gop_budget]['purchased_amt'] += item.purchased_amt
                gop_budget_dict[key_gop_budget]['dif_amt_used'] += item.dif_amt_used
                gop_budget_dict[key_gop_budget]['amt_used'] += item.amt_used
                gop_budget_dict[key_gop_budget]['amount_return'] += item.amount_return
            else:
                gop_budget_dict[key_gop_budget] = {
                    'cs_equipment_gop_id': item.cs_equipment_id.equipment_gop_id.id,
                    'project_scope': item.project_scope.id,
                    'section_name': item.section_name.id,
                    'group_of_product': item.group_of_product.id,
                    'amount_total': item.amount_total,
                    'unallocated_amount': item.cs_equipment_id.equipment_gop_id.product_amt_na,
                    'budget_amount': item.budget_amount,
                    'carried_amt': item.carried_amt,
                    'carry_amt': item.carry_amt,
                    'amt_res': item.amt_res,
                    'billed_amt': item.billed_amt,
                    'purchased_amt': item.purchased_amt,
                    'dif_amt_used': item.dif_amt_used,
                    'amt_used': item.amt_used,
                    'amount_return': item.amount_return,
                }

        self.budget_equipment_gop_ids = [(0, 0, item) for k, item in gop_budget_dict.items()]

    # Material
    def _get_material_from_cs(self, material):
        return {
            'budget_id': self.id,
            'project_scope': material.project_scope.id,
            'section_name': material.section_name.id,
            'variable': material.variable_ref.id,
            'group_of_product': material.group_of_product.id,
            'product_id': material.product_id.id,
            'quantity': material.product_qty,
            'description': material.description,
            'uom_id': material.uom_id.id,
            'budget_quantity': material.product_qty,
            'amount': material.price_unit,
            'budget_amount': material.material_amount_total,
            'unallocated_quantity': material.product_qty_na,
            'unallocated_amount': material.product_amt_na,
        }

    def _get_labour_from_cs(self, labour):
        return {
            'budget_id': self.id,
            'project_scope': labour.project_scope.id,
            'section_name': labour.section_name.id,
            'variable': labour.variable_ref.id,
            'group_of_product': labour.group_of_product.id,
            'product_id': labour.product_id.id,
            'quantity': labour.product_qty,
            'description': labour.description,
            'uom_id': labour.uom_id.id,
            'budget_quantity': labour.product_qty,
            'contractors': labour.contractors,
            'time': labour.unallocated_budget_time,
            'amount': labour.price_unit,
            'budget_amount': labour.labour_amount_total,
            'unallocated_contractors': labour.unallocated_contractors,
            'unallocated_time': labour.unallocated_budget_time,
            'unallocated_quantity': labour.product_qty_na,
            'unallocated_amount': labour.product_amt_na,
        }

    def _get_subcon_from_cs(self, subcon):
        return {
            'budget_id': self.id,
            'project_scope': subcon.project_scope.id,
            'section_name': subcon.section_name.id,
            'subcon_id': subcon.variable.id,
            'quantity': subcon.product_qty,
            'description': subcon.description,
            'uom_id': subcon.uom_id.id,
            'budget_quantity': subcon.product_qty,
            'amount': subcon.price_unit,
            'budget_amount': subcon.subcon_amount_total,
            'unallocated_quantity': subcon.product_qty_na,
            'unallocated_amount': subcon.product_amt_na,
        }

    def _get_overhead_from_cs(self, overhead):
        return {
            'budget_id': self.id,
            'project_scope': overhead.project_scope.id,
            'section_name': overhead.section_name.id,
            'variable': overhead.variable_ref.id,
            'group_of_product': overhead.group_of_product.id,
            'overhead_catagory': overhead.overhead_catagory,
            'product_id': overhead.product_id.id,
            'quantity': overhead.product_qty,
            'description': overhead.description,
            'uom_id': overhead.uom_id.id,
            'budget_quantity': overhead.product_qty,
            'amount': overhead.price_unit,
            'budget_amount': overhead.overhead_amount_total,
            'unallocated_quantity': overhead.product_qty_na,
            'unallocated_amount': overhead.product_amt_na,
        }

    def _get_equipment_from_cs(self, equipment):
        return {
            'budget_id': self.id,
            'project_scope': equipment.project_scope.id,
            'section_name': equipment.section_name.id,
            'variable': equipment.variable_ref.id,
            'group_of_product': equipment.group_of_product.id,
            'product_id': equipment.product_id.id,
            'quantity': equipment.product_qty,
            'description': equipment.description,
            'uom_id': equipment.uom_id.id,
            'budget_quantity': equipment.product_qty,
            'amount': equipment.price_unit,
            'budget_amount': equipment.equipment_amount_total,
            'unallocated_quantity': equipment.product_qty_na,
            'unallocated_amount': equipment.product_amt_na,
        }

    def _get_asset_from_cs(self, asset):
        return {
            'project_budget_id': self.id,
            'project_scope_line_id': asset.project_scope.id,
            'section_name': asset.section_name.id,
            'variable_id': asset.variable_id.id,
            'asset_category_id': asset.asset_category_id.id,
            'asset_id': asset.asset_id.id,
            'uom_id': asset.uom_id.id,
            'budgeted_qty': asset.budgeted_qty,
            'price_unit': asset.price_unit,
            'budgeted_amt': asset.budgeted_amt,
            'unallocated_budget_qty': asset.unallocated_budget_qty,
            'unallocated_budget_amt': asset.unallocated_amt,
        }

    # Subcon Budget to PR
    def prepare_purchase_request_budget(self, budget):
        return {
            'branch_id': budget.branch_id.id,
            'origin': budget.cost_sheet.number,
            'company_id': budget.company_id.id,
            'project': budget.project_id.id,
            'cost_sheet': budget.cost_sheet.id,
            'analytic_account_group_ids': [(6, 0, [v.id for v in budget.analytic_group])],
            'is_subcontracting': True,
            'is_services_orders': True,
        }

    def btn_confirm_project(self):
        for rec in self:
            for mat in rec.budget_material_ids:
                for bud in mat.cs_material_id:
                    if mat.quantity > bud.product_qty_na:
                        raise ValidationError(("The material quantity is over the unallocated quantity"))
            for lab in rec.budget_labour_ids:
                for bud in lab.cs_labour_id:
                    # if lab.quantity > bud.product_qty_na:
                    #     raise ValidationError(("The labour quantity is over the unallocated quantity"))
                    if lab.time > bud.unallocated_budget_time:
                        raise ValidationError(("The labour time is over the unallocated time"))
                    if lab.contractors > bud.unallocated_contractors:
                        raise ValidationError(("The labour contractors is over the unallocated contractors"))
            for sub in rec.budget_subcon_ids:
                for bud in sub.cs_subcon_id:
                    if sub.quantity > bud.product_qty_na:
                        raise ValidationError(("The subcon quantity is over the unallocated quantity"))
            for ove in rec.budget_overhead_ids:
                for bud in ove.cs_overhead_id:
                    if ove.quantity > bud.product_qty_na:
                        raise ValidationError(("The overhead quantity is over the unallocated quantity"))
            for equ in rec.budget_equipment_ids:
                for bud in equ.cs_equipment_id:
                    if equ.quantity > bud.product_qty_na:
                        raise ValidationError(("The equipment quantity is over the unallocated quantity"))

            for mat in rec.budget_material_ids:
                allo_qty = 0.00
                allo_amt = 0.00
                for cost in rec.cost_sheet:
                    allo_qty = (mat.cs_material_id.allocated_budget_qty + mat.quantity)
                    allo_amt = (mat.cs_material_id.allocated_budget_amt + mat.amount_total)
                    cost.material_ids = [(1, mat.cs_material_id.id, {
                        'allocated_budget_qty': allo_qty,
                        'allocated_budget_amt': allo_amt,
                    })]
            for lab in rec.budget_labour_ids:
                allo_qty = 0.00
                allo_amt = 0.00
                for cost in rec.cost_sheet:
                    allo_qty = (lab.cs_labour_id.allocated_budget_qty + lab.quantity)
                    allo_time = (lab.cs_labour_id.allocated_budget_time + lab.time)
                    allo_contractors = (lab.cs_labour_id.allocated_contractors + lab.contractors)
                    allo_amt = (lab.cs_labour_id.allocated_budget_amt + lab.amount_total)
                    cost.material_labour_ids = [(1, lab.cs_labour_id.id, {
                        'allocated_budget_qty': allo_qty,
                        'allocated_contractors': allo_contractors,
                        'allocated_budget_time': allo_time,
                        'allocated_budget_amt': allo_amt,
                    })]

            for sub in rec.budget_subcon_ids:
                allo_qty = 0.00
                allo_amt = 0.00
                for cost in rec.cost_sheet:
                    allo_qty = (sub.cs_subcon_id.allocated_budget_qty + sub.quantity)
                    allo_amt = (sub.cs_subcon_id.allocated_budget_amt + sub.amount_total)
                    cost.material_subcon_ids = [(1, sub.cs_subcon_id.id, {
                        'allocated_budget_qty': allo_qty,
                        'allocated_budget_amt': allo_amt,
                    })]

            for ove in rec.budget_overhead_ids:
                allo_qty = 0.00
                allo_amt = 0.00
                for cost in rec.cost_sheet:
                    allo_qty = (ove.cs_overhead_id.allocated_budget_qty + ove.quantity)
                    allo_amt = (ove.cs_overhead_id.allocated_budget_amt + ove.amount_total)
                    cost.material_overhead_ids = [(1, ove.cs_overhead_id.id, {
                        'allocated_budget_qty': allo_qty,
                        'allocated_budget_amt': allo_amt,
                    })]
            for equ in rec.budget_equipment_ids:
                allo_qty = 0.00
                allo_amt = 0.00
                for cost in rec.cost_sheet:
                    allo_qty = (equ.cs_equipment_id.allocated_budget_qty + equ.quantity)
                    allo_amt = (equ.cs_equipment_id.allocated_budget_amt + equ.amount_total)
                    cost.material_equipment_ids = [(1, equ.cs_equipment_id.id, {
                        'allocated_budget_qty': allo_qty,
                        'allocated_budget_amt': allo_amt,
                    })]

            for ase in rec.budget_internal_asset_ids:
                allo_qty = 0.00
                allo_amt = 0.00
                for cost in rec.cost_sheet:
                    allo_qty = (ase.cs_internal_asset_id.allocated_budget_qty + ase.budgeted_qty)
                    allo_amt = (ase.cs_internal_asset_id.allocated_budget_amt + ase.budgeted_amt)
                    cost.internal_asset_ids = [(1, ase.cs_internal_asset_id.id, {
                        'allocated_budget_qty': allo_qty,
                        'allocated_budget_amt': allo_amt,
                    })]

            rec.cost_sheet.get_gop_material_table()
            rec.cost_sheet.get_gop_labour_table()
            rec.cost_sheet.get_gop_overhead_table()
            rec.cost_sheet.get_gop_equipment_table()

    def button_recompute_line(self):
        for rec in self:
            rec.budget_material_ids.unlink()
            rec.budget_labour_ids.unlink()
            rec.budget_subcon_ids.unlink()
            rec.budget_overhead_ids.unlink()
            rec.budget_equipment_ids.unlink()
            rec.budget_internal_asset_ids.unlink()
            rec.budget_material_gop_ids.unlink()
            rec.budget_labour_gop_ids.unlink()
            rec.budget_overhead_gop_ids.unlink()
            rec.budget_equipment_gop_ids.unlink()

            if rec.project_scope_ids:
                for cos in rec.cost_sheet:
                    for material in cos.material_ids:
                        if material.product_qty_na > 0:
                            if rec.project_scope_ids and rec.section_ids:
                                if (material.project_scope.id in rec.project_scope_ids.ids
                                        and material.section_name.id in rec.section_ids.ids):
                                    # rec.budget_material_ids = [(0, 0, rec._get_material_from_cs(material))]
                                    budget_material_line = rec.budget_material_ids.create(
                                        rec._get_material_from_cs(material))
                                    budget_material_line._onchange_set_cost_sheet_line()
                            elif rec.project_scope_ids and not rec.section_ids:
                                if material.project_scope.id in rec.project_scope_ids.ids:
                                    budget_material_line = rec.budget_material_ids.create(
                                        rec._get_material_from_cs(material))
                                    budget_material_line._onchange_set_cost_sheet_line()
                    for labour in cos.material_labour_ids:
                        if labour.unallocated_budget_time > 0 and labour.unallocated_contractors > 0:
                            if rec.project_scope_ids and rec.section_ids:
                                if (labour.project_scope.id in rec.project_scope_ids.ids
                                        and labour.section_name.id in rec.section_ids.ids):
                                    # rec.budget_labour_ids = [(0, 0, rec._get_labour_from_cs(labour))]
                                    budget_labour_line = rec.budget_labour_ids.create(rec._get_labour_from_cs(labour))
                                    budget_labour_line._onchange_set_cost_sheet_line()
                            elif rec.project_scope_ids and not rec.section_ids:
                                if labour.project_scope.id in rec.project_scope_ids.ids:
                                    budget_labour_line = rec.budget_labour_ids.create(rec._get_labour_from_cs(labour))
                                    budget_labour_line._onchange_set_cost_sheet_line()
                    for subcon in cos.material_subcon_ids:
                        if subcon.product_qty_na > 0:
                            if rec.project_scope_ids and rec.section_ids:
                                if (subcon.project_scope.id in rec.project_scope_ids.ids
                                        and subcon.section_name.id in rec.section_ids.ids):
                                    # rec.budget_subcon_ids = [(0, 0, rec._get_subcon_from_cs(subcon))]
                                    budget_subcon_line = rec.budget_subcon_ids.create(rec._get_subcon_from_cs(subcon))
                                    budget_subcon_line._onchange_set_cost_sheet_line()
                            elif rec.project_scope_ids and not rec.section_ids:
                                if subcon.project_scope.id in rec.project_scope_ids.ids:
                                    budget_subcon_line = rec.budget_subcon_ids.create(rec._get_subcon_from_cs(subcon))
                                    budget_subcon_line._onchange_set_cost_sheet_line()
                    for overhead in cos.material_overhead_ids:
                        if overhead.product_qty_na:
                            if rec.project_scope_ids and rec.section_ids:
                                if (overhead.project_scope.id in rec.project_scope_ids.ids
                                        and overhead.section_name.id in rec.section_ids.ids):
                                    # rec.budget_overhead_ids = [(0, 0, rec._get_overhead_from_cs(overhead))]
                                    budget_overhead_line = rec.budget_overhead_ids.create(
                                        rec._get_overhead_from_cs(overhead))
                                    budget_overhead_line._onchange_set_cost_sheet_line()
                            elif rec.project_scope_ids and not rec.section_ids:
                                if overhead.project_scope.id in rec.project_scope_ids.ids:
                                    budget_overhead_line = rec.budget_overhead_ids.create(
                                        rec._get_overhead_from_cs(overhead))
                                    budget_overhead_line._onchange_set_cost_sheet_line()
                    for equipment in cos.material_equipment_ids:
                        if equipment.product_qty_na:
                            if rec.project_scope_ids and rec.section_ids:
                                if (equipment.project_scope.id in rec.project_scope_ids.ids
                                        and equipment.section_name.id in rec.section_ids.ids):
                                    # rec.budget_equipment_ids = [(0, 0, rec._get_equipment_from_cs(equipment))]
                                    budget_equipment_line = rec.budget_equipment_ids.create(
                                        rec._get_equipment_from_cs(equipment))
                                    budget_equipment_line._onchange_set_cost_sheet_line()
                            elif rec.project_scope_ids and not rec.section_ids:
                                if equipment.project_scope.id in rec.project_scope_ids.ids:
                                    budget_equipment_line = rec.budget_equipment_ids.create(
                                        rec._get_equipment_from_cs(equipment))
                                    budget_equipment_line._onchange_set_cost_sheet_line()
                    for asset in cos.internal_asset_ids:
                        if asset.unallocated_budget_qty:
                            if rec.project_scope_ids and rec.section_ids:
                                if (asset.project_scope.id in rec.project_scope_ids.ids
                                        and asset.section_name.id in rec.section_ids.ids):
                                    # rec.budget_internal_asset_ids = [(0, 0, rec._get_asset_from_cs(asset))]
                                    budget_internal_asset_line = rec.budget_internal_asset_ids.create(
                                        rec._get_asset_from_cs(asset))
                                    budget_internal_asset_line._onchange_set_cost_sheet_line()
                            elif rec.project_scope_ids and not rec.section_ids:
                                if asset.project_scope.id in rec.project_scope_ids.ids:
                                    budget_internal_asset_line = rec.budget_internal_asset_ids.create(
                                        rec._get_asset_from_cs(asset))
                                    budget_internal_asset_line._onchange_set_cost_sheet_line()

                    if not rec.budget_material_ids and not rec.budget_labour_ids and not rec.budget_overhead_ids and not rec.budget_equipment_ids and not rec.budget_subcon_ids and not rec.budget_internal_asset_ids:
                        raise ValidationError(
                            "There is no unallocated budget left on this project, please select another project!")

                    rec.project_scope_ids = False
                    rec.section_ids = False

                rec.get_gop_material_table()
                rec.get_gop_labour_table()
                rec.get_gop_overhead_table()
                rec.get_gop_equipment_table()

    def button_refresh_line(self):
        for rec in self:
            for mat in rec.budget_material_ids:
                if mat.cs_material_id.product_qty_na == 0:
                    rec.budget_material_ids = [(2, mat.id)]
                    continue
                if mat.quantity >= mat.cs_material_id.product_qty_na:
                    rec.budget_material_ids = [(1, mat.id, {
                        'quantity': mat.cs_material_id.product_qty_na
                    })]
                    rec.budget_material_ids._get_unallocated()
            for lab in rec.budget_labour_ids:
                if lab.cs_labour_id.unallocated_budget_time == 0 or lab.cs_labour_id.unallocated_contractors == 0:
                    rec.budget_labour_ids = [(2, lab.id)]
                    continue
                if lab.time >= lab.cs_labour_id.unallocated_budget_time:
                    rec.budget_labour_ids = [(1, lab.id, {
                        'time': lab.cs_labour_id.unallocated_budget_time
                    })]
                    rec.budget_labour_ids._get_unallocated()
                if lab.contractors >= lab.cs_labour_id.unallocated_contractors:
                    rec.budget_labour_ids = [(1, lab.id, {
                        'contractors': lab.cs_labour_id.unallocated_contractors
                    })]
                    rec.budget_labour_ids._get_unallocated()
            for sub in rec.budget_subcon_ids:
                if sub.cs_subcon_id.product_qty_na == 0:
                    rec.budget_subcon_ids = [(2, sub.id)]
                    continue
                if sub.quantity >= sub.cs_subcon_id.product_qty_na:
                    rec.budget_subcon_ids = [(1, sub.id, {
                        'quantity': sub.cs_subcon_id.product_qty_na
                    })]
                    rec.budget_subcon_ids._get_unallocated()
            for ove in rec.budget_overhead_ids:
                if ove.cs_overhead_id.product_qty_na == 0:
                    rec.budget_overhead_ids = [(2, ove.id)]
                    continue
                if ove.quantity >= ove.cs_overhead_id.product_qty_na:
                    rec.budget_overhead_ids = [(1, ove.id, {
                        'quantity': ove.cs_overhead_id.product_qty_na
                    })]
                    rec.budget_overhead_ids._get_unallocated()
            for asset in rec.budget_internal_asset_ids:
                if asset.cs_internal_asset_id.unallocated_budget_qty == 0:
                    rec.budget_internal_asset_ids = [(2, asset.id)]
                    continue
                if asset.budgeted_qty >= asset.cs_internal_asset_id.unallocated_budget_qty:
                    rec.budget_internal_asset_ids = [(1, asset.id, {
                        'budgeted_qty': asset.cs_internal_asset_id.unallocated_budget_qty
                    })]
                    rec.budget_internal_asset_ids._get_unallocated()
            for equ in rec.budget_equipment_ids:
                if equ.cs_equipment_id.product_qty_na == 0:
                    rec.budget_equipment_ids = [(2, equ.id)]
                    continue
                if equ.quantity >= equ.cs_equipment_id.product_qty_na:
                    rec.budget_equipment_ids = [(1, equ.id, {
                        'quantity': equ.cs_equipment_id.product_qty_na
                    })]
                    rec.budget_equipment_ids._get_unallocated()

            rec.is_must_refresh = False
            rec.get_gop_material_table()
            rec.get_gop_labour_table()
            rec.get_gop_overhead_table()
            rec.get_gop_equipment_table()

    def btn_confirm(self):
        for rec in self:
            total_line = (len(rec.budget_material_ids) + len(rec.budget_labour_ids)
                          + len(rec.budget_overhead_ids)
                          + len(rec.budget_internal_asset_ids) + len(rec.budget_equipment_ids)
                          + len(rec.budget_subcon_ids))

            if total_line == 0:
                raise ValidationError(
                    _("There's no budget estimation for this periodical budget. "
                      "You have to add a line first."))

            rec.btn_confirm_project()
            rec.state = 'in_progress'

    # def button_material_claim_budget(self):
    #     for rec in self:
    #         free_amt = 0.00
    #         for material in rec.budget_material_ids:
    #             if material.is_has_budget_left:
    #                 free_amt += material.amt_left
    #                 material.write({'amount_return': material.amt_left,
    #                                 'is_has_budget_left': False
    #                                 })
    #                 material.cs_material_id.write({
    #                     'amount_return': material.cs_material_id.amount_return + material.amt_left,
    #                     'is_has_budget_left': False,
    #                 })
    #                 if rec.budgeting_method == 'gop_budget':
    #                     # rec.get_gop_material_table()
    #                     budget_material_gop = rec.budget_material_gop_ids.filtered(
    #                         lambda x: x.group_of_product.id == material.group_of_product.id)
    #                     budget_material_gop.amount_return += material.amt_left
    #                     budget_material_gop._budget_amount_left()
    #
    #                     cost_sheet_material_gop = rec.cost_sheet.material_gop_ids.filtered(
    #                         lambda x: x.group_of_product.id == material.group_of_product.id)
    #                     cost_sheet_material_gop.amount_return += material.amt_left
    #                     cost_sheet_material_gop._budget_amount_left()
    #                 rec.cost_sheet.write({
    #                     'material_budget_claim_history_cost_ids': [(0, 0, {
    #                         'job_sheet_id': rec.cost_sheet.id,
    #                         'type': 'material',
    #                         'project_scope_id': material.project_scope.id,
    #                         'section_id': material.section_name.id,
    #                         'group_of_product_id': material.group_of_product.id,
    #                         'product_id': material.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': material.uom_id.id,
    #                         'budget_amount': material.amount_total,
    #                         'budget_claim_amount': material.amount_return,
    #                     })],
    #                 })
    #                 rec.write({
    #                     'material_budget_claim_history_ids': [(0, 0, {
    #                         'project_budget_id': rec.id,
    #                         'type': 'material',
    #                         'project_scope_id': material.project_scope.id,
    #                         'section_id': material.section_name.id,
    #                         'group_of_product_id': material.group_of_product.id,
    #                         'product_id': material.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': material.uom_id.id,
    #                         'budget_amount': material.amount_total,
    #                         'budget_claim_amount': material.amount_return,
    #                     })],
    #                 })
    #                 material._budget_amount_left()
    #
    #         if free_amt > 0:
    #             rec.cost_sheet.write({
    #                 'amount_from_budget': rec.cost_sheet.amount_from_budget + free_amt,
    #             })
    #
    # def button_labour_claim_budget(self):
    #     for rec in self:
    #         free_amt = 0.00
    #         for labour in rec.budget_labour_ids:
    #             if labour.is_has_budget_left:
    #                 free_amt += labour.amt_left
    #                 labour.write({
    #                     'amount_return': labour.amt_left,
    #                     'is_has_budget_left': False,
    #                 })
    #                 labour.cs_labour_id.write({
    #                     'amount_return': labour.cs_labour_id.amount_return + labour.amt_left,
    #                     'is_has_budget_left': False,
    #                 })
    #                 if rec.budgeting_method == 'gop_budget':
    #                     # rec.get_gop_labour_table()
    #                     budget_labour_gop = rec.budget_labour_gop_ids.filtered(
    #                         lambda x: x.group_of_product.id == labour.group_of_product.id)
    #                     budget_labour_gop.amount_return += labour.amt_left
    #                     budget_labour_gop._budget_amount_left()
    #
    #                     cost_sheet_labour_gop = rec.cost_sheet.material_labour_gop_ids.filtered(
    #                         lambda x: x.group_of_product.id == labour.group_of_product.id)
    #                     cost_sheet_labour_gop.amount_return += labour.amt_left
    #                     cost_sheet_labour_gop._budget_amount_left()
    #
    #                 rec.cost_sheet.write({
    #                     'labour_budget_claim_history_cost_ids': [(0, 0, {
    #                         'job_sheet_id': rec.cost_sheet.id,
    #                         'type': 'labour',
    #                         'project_scope_id': labour.project_scope.id,
    #                         'section_id': labour.section_name.id,
    #                         'group_of_product_id': labour.group_of_product.id,
    #                         'product_id': labour.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': labour.uom_id.id,
    #                         'budget_amount': labour.amount_total,
    #                         'budget_claim_amount': labour.amount_return,
    #                     })],
    #                 })
    #                 rec.write({
    #                     'labour_budget_claim_history_ids': [(0, 0, {
    #                         'project_budget_id': rec.id,
    #                         'type': 'labour',
    #                         'project_scope_id': labour.project_scope.id,
    #                         'section_id': labour.section_name.id,
    #                         'group_of_product_id': labour.group_of_product.id,
    #                         'product_id': labour.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': labour.uom_id.id,
    #                         'budget_amount': labour.amount_total,
    #                         'budget_claim_amount': labour.amount_return,
    #                     })],
    #                 })
    #                 labour._budget_amount_left()
    #         if free_amt > 0:
    #             rec.cost_sheet.write({
    #                 'amount_from_budget': rec.cost_sheet.amount_from_budget + free_amt
    #             })
    #
    # def button_overhead_claim_budget(self):
    #     for rec in self:
    #         free_amt = 0.00
    #         for overhead in rec.budget_overhead_ids:
    #             if overhead.is_has_budget_left:
    #                 free_amt += overhead.amt_left
    #                 overhead.write({'amount_return': overhead.amt_left,
    #                                 'is_has_budget_left': False
    #                                 })
    #                 overhead.cs_overhead_id.write({
    #                     'amount_return': overhead.cs_overhead_id.amount_return + overhead.amt_left,
    #                     'is_has_budget_left': False,
    #                 })
    #                 if rec.budgeting_method == 'gop_budget':
    #                     # rec.get_gop_overhead_table()
    #                     budget_overhead_gop = rec.budget_overhead_gop_ids.filtered(
    #                         lambda x: x.group_of_product.id == overhead.group_of_product.id)
    #                     budget_overhead_gop.amount_return += overhead.amt_left
    #                     budget_overhead_gop._budget_amount_left()
    #
    #                     cost_sheet_overhead_gop = rec.cost_sheet.material_overhead_gop_ids.filtered(
    #                         lambda x: x.group_of_product.id == overhead.group_of_product.id)
    #                     cost_sheet_overhead_gop.amount_return += overhead.amt_left
    #                     cost_sheet_overhead_gop._budget_amount_left()
    #
    #                 rec.cost_sheet.write({
    #                     'overhead_budget_claim_history_cost_ids': [(0, 0, {
    #                         'job_sheet_id': rec.cost_sheet.id,
    #                         'type': 'overhead',
    #                         'project_scope_id': overhead.project_scope.id,
    #                         'section_id': overhead.section_name.id,
    #                         'group_of_product_id': overhead.group_of_product.id,
    #                         'product_id': overhead.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': overhead.uom_id.id,
    #                         'budget_amount': overhead.amount_total,
    #                         'budget_claim_amount': overhead.amount_return,
    #                     })],
    #                 })
    #                 rec.write({
    #                     'overhead_budget_claim_history_ids': [(0, 0, {
    #                         'project_budget_id': rec.id,
    #                         'type': 'overhead',
    #                         'project_scope_id': overhead.project_scope.id,
    #                         'section_id': overhead.section_name.id,
    #                         'group_of_product_id': overhead.group_of_product.id,
    #                         'product_id': overhead.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': overhead.uom_id.id,
    #                         'budget_amount': overhead.amount_total,
    #                         'budget_claim_amount': overhead.amount_return,
    #                     })],
    #                 })
    #                 overhead._budget_amount_left()
    #         if free_amt > 0:
    #             rec.cost_sheet.write({
    #                 'amount_from_budget': rec.cost_sheet.amount_from_budget + free_amt
    #             })
    #
    # def button_equipment_claim_budget(self):
    #     for rec in self:
    #         free_amt = 0.00
    #         for equipment in rec.budget_equipment_ids:
    #             if equipment.is_has_budget_left:
    #                 free_amt += equipment.amt_left
    #                 equipment.write({'amount_return': equipment.amt_left,
    #                                  'is_has_budget_left': False
    #                                  })
    #                 equipment.cs_equipment_id.write({
    #                     'amount_return': equipment.cs_equipment_id.amount_return + equipment.amt_left,
    #                     'is_has_budget_left': False,
    #                 })
    #                 if rec.budgeting_method == 'gop_budget':
    #                     # rec.get_gop_equipment_table()
    #                     budget_equipment_gop = rec.budget_equipment_gop_ids.filtered(
    #                         lambda x: x.group_of_product.id == equipment.group_of_product.id)
    #                     budget_equipment_gop.amount_return += equipment.amt_left
    #                     budget_equipment_gop._budget_amount_left()
    #
    #                     cost_sheet_equipment_gop = rec.cost_sheet.material_equipment_gop_ids.filtered(
    #                         lambda x: x.group_of_product.id == equipment.group_of_product.id)
    #                     cost_sheet_equipment_gop.amount_return += equipment.amt_left
    #                     cost_sheet_equipment_gop._budget_amount_left()
    #
    #                 rec.cost_sheet.write({
    #                     'equipment_budget_claim_history_cost_ids': [(0, 0, {
    #                         'job_sheet_id': rec.cost_sheet.id,
    #                         'type': 'equipment',
    #                         'project_scope_id': equipment.project_scope.id,
    #                         'section_id': equipment.section_name.id,
    #                         'group_of_product_id': equipment.group_of_product.id,
    #                         'product_id': equipment.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': equipment.uom_id.id,
    #                         'budget_amount': equipment.amount_total,
    #                         'budget_claim_amount': equipment.amount_return,
    #                     })],
    #                 })
    #                 rec.write({
    #                     'equipment_budget_claim_history_ids': [(0, 0, {
    #                         'project_budget_id': rec.id,
    #                         'type': 'equipment',
    #                         'project_scope_id': equipment.project_scope.id,
    #                         'section_id': equipment.section_name.id,
    #                         'group_of_product_id': equipment.group_of_product.id,
    #                         'product_id': equipment.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': equipment.uom_id.id,
    #                         'budget_amount': equipment.amount_total,
    #                         'budget_claim_amount': equipment.amount_return,
    #                     })],
    #                 })
    #                 equipment._budget_amount_left()
    #         if free_amt > 0:
    #             rec.cost_sheet.write({
    #                 'amount_from_budget': rec.cost_sheet.amount_from_budget + free_amt
    #             })
    #
    # def button_subcon_claim_budget(self):
    #     for rec in self:
    #         free_amt = 0.00
    #         for subcon in rec.budget_subcon_ids:
    #             if subcon.is_has_budget_left:
    #                 free_amt += subcon.amt_left
    #                 subcon.write({'amount_return': subcon.amt_left,
    #                               'is_has_budget_left': False
    #                               })
    #                 subcon.cs_subcon_id.write({
    #                     'amount_return': subcon.cs_subcon_id.amount_return + subcon.amt_left,
    #                     'is_has_budget_left': False,
    #                 })
    #                 rec.cost_sheet.write({
    #                     'subcon_budget_claim_history_cost_ids': [(0, 0, {
    #                         'job_sheet_id': rec.cost_sheet.id,
    #                         'type': 'subcon',
    #                         'project_scope_id': subcon.project_scope.id,
    #                         'section_id': subcon.section_name.id,
    #                         # 'group_of_product_id': subcon.group_of_product.id,
    #                         # 'product_id': subcon.product_id.id,
    #                         'subcon_id': subcon.id,
    #                         'uom_id': subcon.uom_id.id,
    #                         'budget_amount': subcon.amount_total,
    #                         'budget_claim_amount': subcon.amount_return,
    #                     })],
    #                 })
    #                 rec.write({
    #                     'subcon_budget_claim_history_ids': [(0, 0, {
    #                         'project_budget_id': rec.id,
    #                         'type': 'subcon',
    #                         'project_scope_id': subcon.project_scope.id,
    #                         'section_id': subcon.section_name.id,
    #                         # 'group_of_product_id': subcon.group_of_product.id,
    #                         # 'product_id': subcon.product_id.id,
    #                         'subcon_id': subcon.id,
    #                         'uom_id': subcon.uom_id.id,
    #                         'budget_amount': subcon.amount_total,
    #                         'budget_claim_amount': subcon.amount_return,
    #                     })],
    #                 })
    #                 subcon._budget_amount_left()
    #         if free_amt > 0:
    #             rec.cost_sheet.write({
    #                 'amount_from_budget': rec.cost_sheet.amount_from_budget + free_amt
    #             })

    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines",
                                              compute='get_scope_lines')

    @api.depends('project_id.project_scope_ids')
    def get_scope_lines(self):
        for rec in self:
            pro = rec.project_id
            scope_ids = []
            if pro.project_scope_ids:
                for line in pro.project_scope_ids:
                    if line.project_scope:
                        scope_ids.append(line.project_scope.id)
                rec.project_scope_computed = [(6, 0, scope_ids)]
            else:
                rec.project_scope_computed = [(6, 0, [])]

    @api.onchange('project_scope_ids', 'section_ids')
    def _onchange_section_ids(self):
        for rec in self:
            section_ids = []
            if rec.project_id.project_section_ids:
                for line in rec.project_id.project_section_ids:
                    if line.section and line.project_scope.id in rec.project_scope_ids.ids:
                        section_ids.append(line.section.id)

                # Remove section if corresponding scope is removed
                for section in rec.section_ids:
                    # if (rec.project_id.project_section_ids.filtered(
                    #         lambda x: x.section.id == section._origin.id).project_scope.id
                    #         not in rec.project_scope_ids.ids):
                    #     rec.section_ids = [(3, section.id)]
                    project_sections = rec.project_id.project_section_ids.filtered(
                            lambda x: x.section.id == section._origin.id)
                    is_exist = False
                    for item in project_sections:
                        if item.project_scope.id in rec.project_scope_ids.ids:
                            is_exist = True
                    if not is_exist:
                        rec.section_ids = [(3, section.id)]
            return {'domain': {'section_ids': [('id', 'in', section_ids)]}}

    @api.onchange('project_id')
    def _onchange_project_id(self):
        for rec in self:
            for proj in rec.project_id:
                cost = rec.env['job.cost.sheet'].search(
                    [('project_id', '=', rec.project_id.id), ('state', '=', 'in_progress')])
                if not cost:
                    raise ValidationError("Please in progress the cost sheet first!")
                else:
                    rec.analytic_group_id = proj.analytic_idz
                    rec.write({'cost_sheet': cost})

    # Validation cannot add line same as existing line
    @api.onchange('budget_material_ids')
    def _check_exist_group_of_product_material(self):
        exist_section_group_list_material = []
        for line in self.budget_material_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_material):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_material.append(same)

    @api.onchange('budget_labour_ids')
    def _check_exist_group_of_product_labour(self):
        exist_section_group_list_labour1 = []
        for line in self.budget_labour_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_labour1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_labour1.append(same)

    @api.onchange('budget_overhead_ids')
    def _check_exist_group_of_product_overhead(self):
        exist_section_group_list_overhead = []
        for line in self.budget_overhead_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_overhead):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_overhead.append(same)

    @api.onchange('budget_equipment_ids')
    def _check_exist_group_of_product_equipment(self):
        exist_section_group_list_equipment1 = []
        for line in self.budget_equipment_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_equipment1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_equipment1.append(same)

    @api.onchange('budget_internal_asset_ids')
    def _check_exist_group_of_product_asset(self):
        exist_section_group_list_asset1 = []
        for line in self.budget_internal_asset_ids:
            same = str(line.project_scope_line_id.id) + ' - ' + str(line.section_name.id) + ' - ' + str(
                line.asset_id.id)
            if (same in exist_section_group_list_asset1):
                raise ValidationError(
                    _('The Asset "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Asset selected.' % (
                        (line.asset_id.name), (line.project_scope_line_id.name), (line.section_name.name))))
            exist_section_group_list_asset1.append(same)

    @api.onchange('budget_subcon_ids')
    def _check_exist_subcon(self):
        exist_section_subcon_list_subcon = []
        for line in self.budget_subcon_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.subcon_id.id)
            if (same in exist_section_subcon_list_subcon):
                raise ValidationError(
                    _('The Job Subcon "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Job Subcon selected.' % (
                        (line.subcon_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_subcon_list_subcon.append(same)

    @api.constrains('budget_material_ids')
    def _check_exist_group_of_product_material_2(self):
        exist_section_group_list_material = []
        for line in self.budget_material_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_material):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_material.append(same)

    @api.constrains('budget_labour_ids')
    def _check_exist_group_of_product_labour_2(self):
        exist_section_group_list_labour1 = []
        for line in self.budget_labour_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_labour1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_labour1.append(same)

    @api.constrains('budget_overhead_ids')
    def _check_exist_group_of_product_overhead_2(self):
        exist_section_group_list_overhead = []
        for line in self.budget_overhead_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_overhead):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_overhead.append(same)

    @api.constrains('budget_equipment_ids')
    def _check_exist_group_of_product_equipment_2(self):
        exist_section_group_list_equipment1 = []
        for line in self.budget_equipment_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_equipment1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_equipment1.append(same)

    @api.constrains('budget_internal_asset_ids')
    def _check_exist_group_of_product_asset_2(self):
        exist_section_group_list_asset1 = []
        for line in self.budget_internal_asset_ids:
            same = str(line.project_scope_line_id.id) + ' - ' + str(line.section_name.id) + ' - ' + str(
                line.asset_id.id)
            if (same in exist_section_group_list_asset1):
                raise ValidationError(
                    _('The Asset "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Asset selected.' % (
                        (line.asset_id.name), (line.project_scope_line_id.name), (line.section_name.name))))
            exist_section_group_list_asset1.append(same)

    @api.constrains('budget_subcon_ids')
    def _check_exist_subcon_2(self):
        exist_section_subcon_list_subcon = []
        for line in self.budget_subcon_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.subcon_id.id)
            if (same in exist_section_subcon_list_subcon):
                raise ValidationError(
                    _('The Job Subcon "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Job Subcon selected.' % (
                        (line.subcon_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_subcon_list_subcon.append(same)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError("You can not delete a record which is not in draft state.")
        return super(ProjectBudget, self).unlink()


class ProjectBudgetApproverUser(models.Model):
    _name = 'project.budget.approver.user'
    _description = "Project Budget Approver User"

    project_budget_approver_id = fields.Many2one('project.budget', string="Periodical Budget")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'project_budget_app_emp_ids', string="Approved user")
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
    matrix_user_ids = fields.Many2many('res.users', 'budget_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    # parent status
    state = fields.Selection(related='project_budget_approver_id.state', string='Parent Status')

    @api.depends('project_budget_approver_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.project_budget_approver_id.project_budget_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len(rec.user_ids) < rec.minimum_approver and rec.project_budget_approver_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.project_budget_approver_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids


class BudgetMaterials(models.Model):
    _name = 'budget.material'
    _description = "Budget Materials"
    _order = 'sequence'
    _check_company_auto = True

    budget_id = fields.Many2one('project.budget', string='Budget')
    cs_material_id = fields.Many2one('material.material', 'Material ID')
    budget_carry_over_id = fields.Many2one('project.budget.carry', string="Budget Carry Over")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product',
                                 check_company=True, required=True)
    description = fields.Text('Description')
    billed_qty = fields.Float('Billed Quantity', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    purchased_qty = fields.Float('Purchased Quantity', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    quantity = fields.Float(string="Budget Quantity", default=0)
    qty_left = fields.Float(string='Budget Quantity Left', compute="_budget_quantity_left")
    qty_res = fields.Float(string='Reserved Budget Quantity')
    qty_used = fields.Float('Actual Used Quantity', default=0.00)
    transferred_qty = fields.Float('Transferred Quantity')
    transferred_amt = fields.Float('Transferred Amount')
    qty_received = fields.Float('Received Quantity')
    budget_quantity = fields.Float(string="Sheet Budget Quantity")
    unallocated_quantity = fields.Float(string="Unallocated Budget Quantity")
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    amount = fields.Float(string="Unit Price", default=0.00)
    amount_total = fields.Float(string="Budget Amount", compute="_amount_total_comute")
    amt_left = fields.Float(string='Budget Amount Left', compute="_budget_amount_left")
    amt_res = fields.Float(string='Reserved Budget Amount')
    amt_used = fields.Float('Actual Used Amount', default=0.00)
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    dif_qty_used = fields.Float('Actual Used Quantity on different budget', default=0.00)
    dif_amt_used = fields.Float('Actual Used Amount on different budget', default=0.00)
    budget_amount = fields.Float(string="Sheet Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Budget Amount")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    on_hand_qty = fields.Float(string='On Hand Quantity', related='cs_material_id.on_hand_qty')
    on_hand_qty_converted = fields.Float(related='cs_material_id.on_hand_qty_converted')
    # Carry Over
    carried_qty = fields.Float('Carried Quantity (receive)', default=0.00)
    carried_amt = fields.Float('Carried Amount (receive)', default=0.00)
    carry_qty = fields.Float('Carried Quantity (send)', default=0.00)
    carry_amt = fields.Float('Carried Amount (send)', default=0.00)
    status = fields.Selection([('carry_to', ' Carried to'),
                               ('carry_from', 'Carried From'),
                               ('carried_over', 'Carried Over')],
                              string="Status")
    carried_to = fields.Many2one('project.budget', string='Carried To')
    carried_from = fields.Many2one('project.budget', string='Carried From')
    carried_over = fields.Boolean(string='Carried Over')
    project_id = fields.Many2one(related='budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    material_gop_id = fields.Many2one('material.gop.material', string="Material GOP ID", compute="_get_material_gop_id")
    amount_return = fields.Float('Return Amount', default=0.00)
    reserved_return_amount = fields.Float('Reserved Return Amount', default=0.00)
    over_amount = fields.Float('Over Amount', default=0.00)
    reserved_over_amount = fields.Float('Reserved Over Amount', default=0.00)
    po_reserved_qty = fields.Float('PO Reserved Quantity', default=0.00)

    @api.depends('project_scope', 'section_name', 'group_of_product')
    def _get_material_gop_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product:
                gop_line = self.env['budget.gop.material'].search(
                    [('budget_id', '=', res.budget_id.id), ('project_scope', '=', res.project_scope.id),
                     ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id)],
                    limit=1)
                if gop_line:
                    res.material_gop_id = gop_line.id
                else:
                    res.material_gop_id = False
            else:
                res.material_gop_id = False

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('budget_id.budget_material_ids', 'budget_id.budget_material_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.budget_id.budget_material_ids:
                no += 1
                l.sr_no = no

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'cs_material_id': False,
                    'section_name': False,
                    'variable': False,
                    'group_of_product': False,
                    'product_id': False,
                    'description': False,
                })
        else:
            self.update({
                'cs_material_id': False,
                'section_name': False,
                'variable': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'cs_material_id': False,
                    'variable': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_material_id': False,
                'variable': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable')
    def _onchange_variable_handling(self):
        if self._origin.variable._origin.id:
            if self._origin.variable._origin.id != self.variable.id:
                self.update({
                    'cs_material_id': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_material_id': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self._origin.group_of_product._origin.id:
            if self._origin.group_of_product._origin.id != self.group_of_product.id:
                self.update({
                    'cs_material_id': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_material_id': False,
                'product_id': False,
            })

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

    @api.onchange('quantity')
    def _onchange_quantity(self):
        for rec in self:
            if rec.cs_material_id:
                if rec.quantity > rec.unallocated_quantity:
                    if rec.project_id.budgeting_method == 'gop_budget':
                        raise ValidationError("The allocated group of product amount is over the unallocated amount")
                    else:
                        raise ValidationError("The quantity is over the unallocated quantity")

    @api.onchange('quantity', 'amount')
    def _amount_total_comute(self):
        for line in self:
            # line.amount_total = line.quantity * line.amount
            if (line.qty_res > 0 and line.amt_res > 0) or line.purchased_qty > 0 or (line.transferred_qty and line.transferred_amt):
                current_quantity = line.quantity - line.qty_res - line.purchased_qty - line.transferred_qty
                current_amount_total = current_quantity * line.amount
                if line.qty_res > 0 >= line.po_reserved_qty:
                    previous_unit_price = ((line.amt_res + line.purchased_amt + line.amount_return
                                            + line.transferred_amt + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.qty_res + line.purchased_qty + line.transferred_qty))
                else:
                    previous_unit_price = ((line.amt_res + line.purchased_amt + line.amount_return
                                            + line.transferred_amt + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.po_reserved_qty + line.purchased_qty + line.transferred_qty))
                previous_amount_total = previous_unit_price * (line.purchased_qty + line.qty_res + line.transferred_qty)
                line.amount_total = current_amount_total + previous_amount_total
            else:
                line.amount_total = line.quantity * line.amount

    @api.onchange('quantity', 'qty_res', 'purchased_qty')
    def _budget_quantity_left(self):
        for line in self:
            line.qty_left = line.quantity + line.carried_qty - (
                    line.qty_res + line.purchased_qty + line.transferred_qty + line.carry_qty)

    @api.onchange('amount_total', 'amt_res', 'purchased_amt')
    def _budget_amount_left(self):
        for line in self:
            line.amt_left = line.amount_total + line.carried_amt - (
                    line.amt_res + line.purchased_amt + line.carry_amt + line.amount_return + line.transferred_amt)

    # def _reserved_qty(self):
    #     for line in self:
    #         line.qty_res = line.qty_res - line.purchased_qty

    # def _reserved_amt(self):
    #    for line in self:
    #         line.amt_res = line.amt_res - line.purchased_amt

    def _unused_qty(self):
        for line in self:
            line.unused_qty = line.quantity - line.qty_used - line.dif_qty_used

    def _unused_amt(self):
        for line in self:
            line.unused_amt = line.amount_total - line.amt_used - line.dif_amt_used

    def _get_unallocated(self):
        for line in self:
            if line.cs_material_id:
                line.unallocated_quantity = line.cs_material_id.product_qty_na
                line.unallocated_amount = line.cs_material_id.product_amt_na
            else:
                line.unallocated_quantity = 0
                line.unallocated_amount = 0

    @api.onchange('date')
    def _onchange_domain_gop(self):
        for rec in self:
            cost_sheet = rec.budget_id.cost_sheet
            cs_gop = cost_sheet.material_ids.mapped('group_of_product')

            return {'domain': {'group_of_product': [('id', 'in', cs_gop.ids)]}}

    @api.onchange('group_of_product')
    def _onchange_domain_product(self):
        for rec in self:
            cost_sheet = rec.budget_id.cost_sheet
            cs_product = cost_sheet.material_ids.mapped('product_id')

            return {'domain': {'product_id': [('id', 'in', cs_product.ids),
                                              ('group_of_product', '=', rec.group_of_product.id)]}}

    @api.onchange('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _onchange_set_cost_sheet_line(self):
        for rec in self:
            if rec.project_scope and rec.section_name and rec.group_of_product and rec.product_id:
                cost_sheet_line = rec.env['material.material'].search([
                    ('job_sheet_id', '=', rec.budget_id.cost_sheet.id),
                    ('project_scope', '=', rec.project_scope.id),
                    ('section_name', '=', rec.section_name.id),
                    ('group_of_product', '=', rec.group_of_product.id),
                    ('product_id', '=', rec.product_id.id)])
                if cost_sheet_line:
                    rec.update({
                        'cs_material_id': cost_sheet_line.id,
                        'description': cost_sheet_line.description,
                        'uom_id': cost_sheet_line.uom_id.id,
                        'budget_quantity': cost_sheet_line.product_qty,
                        'amount': cost_sheet_line.price_unit,
                        'budget_amount': cost_sheet_line.material_amount_total,
                        'unallocated_quantity': cost_sheet_line.product_qty_na,
                        'unallocated_amount': cost_sheet_line.product_amt_na,
                    })
                else:
                    raise ValidationError("There is no cost sheet line for this estimation, please select another "
                                          "combination!")

    def _get_id_from_cs(self):
        value = False
        for line in self:
            value = self.env['material.material'].search([('job_sheet_id', '=', line.budget_id.cost_sheet.id),
                                                          ('project_scope', '=', line.project_scope.id),
                                                          ('section_name', '=', line.section_name.id),
                                                          ('group_of_product', '=', line.group_of_product.id),
                                                          ('product_id', '=', line.product_id.id)])
            line.cs_material_id = value


class BudgetLabour(models.Model):
    _name = 'budget.labour'
    _description = "Budget Labour"
    _order = 'sequence'
    _check_company_auto = True

    budget_id = fields.Many2one('project.budget', string='Budget')
    cs_labour_id = fields.Many2one('material.labour', 'Labour ID')
    budget_carry_over_id = fields.Many2one('project.budget.carry', string="Budget Carry Over")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product',
                                 check_company=True, required=True)
    description = fields.Text('Description')
    billed_qty = fields.Float('Billed Quantity', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    purchased_qty = fields.Float('Purchased Quantity', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    quantity = fields.Float(string="Budget Quantity", default=0)
    qty_left = fields.Float(string='Budget Quantity Left', compute="_budget_quantity_left")
    qty_res = fields.Float(string='Reserved Budget Quantity')
    qty_used = fields.Float('Actual Used Quantity', default=0.00)
    time_used = fields.Float('Actual Used TIme', default=0.00)
    transferred_qty = fields.Float('Transferred Quantity')
    transferred_amt = fields.Float('Transferred Amount')
    qty_received = fields.Float('Received Quantity')
    budget_quantity = fields.Float(string="Sheet Budget Quantity")
    unallocated_quantity = fields.Float(string="Unallocated Budget Quantity")
    unallocated_contractors = fields.Integer(string="Unallocated Budget Contractors")
    unallocated_time = fields.Float(string="Unallocated Budget Time")
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    amount = fields.Float(string="Unit Price", default=0.00)
    amount_total = fields.Float(string="Budget Amount", compute="_amount_total_comute")
    amt_left = fields.Float(string='Budget Amount Left', compute="_budget_amount_left")
    amt_res = fields.Float(string='Reserved Budget Amount')
    amt_used = fields.Float('Actual Used Amount', default=0.00)
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_time = fields.Float('Unused Quantity', default=0.00, compute="_unused_time")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    dif_qty_used = fields.Float('Actual Used Quantity on different budget', default=0.00)
    dif_amt_used = fields.Float('Actual Used Amount on different budget', default=0.00)
    budget_amount = fields.Float(string="Sheet Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Budget Amount")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    on_hand_qty = fields.Float(string='On Hand Quantity', related='cs_labour_id.on_hand_qty')
    on_hand_qty_converted = fields.Float(related='cs_labour_id.on_hand_qty_converted')
    # Carry Over
    carried_qty = fields.Float('Carried Quantity (receive)', default=0.00)
    carried_amt = fields.Float('Carried Amount (receive)', default=0.00)
    carry_qty = fields.Float('Carried Quantity (send)', default=0.00)
    carry_amt = fields.Float('Carried Amount (send)', default=0.00)
    status = fields.Selection([('carry_to', ' Carried to'),
                               ('carry_from', 'Carried From'),
                               ('carried_over', 'Carried Over')],
                              string="Status")
    carried_to = fields.Many2one('project.budget', string='Carried To')
    carried_from = fields.Many2one('project.budget', string='Carried From')
    project_id = fields.Many2one(related='budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    labour_gop_id = fields.Many2one('material.gop.labour', string="Labour GOP ID", compute="_get_labour_gop_id")
    amount_return = fields.Float('Return Amount', default=0.00)
    time = fields.Float('Budgeted Time', default=0.00)
    time_left = fields.Float('Budgeted Time Left', default=0.00, compute="_time_left")
    reserved_time = fields.Float('Reserved Budget Time', default=0.00, readonly=True)
    contractors = fields.Integer('Contractors', default=0)
    reserved_contractors = fields.Integer('Reserved Contractors', default=0, readonly=True)
    contractors_left = fields.Integer('Contractors Left', default=0, compute="_contractors_left")

    @api.depends('contractors', 'reserved_contractors')
    def _contractors_left(self):
        for line in self:
            total = line.contractors - line.reserved_contractors
            line.contractors_left = total

    @api.depends('time')
    def _time_left(self):
        total = 0
        for line in self:
            total = line.time - line.reserved_time - line.time_used
            line.time_left = total

    @api.depends('project_scope', 'section_name', 'group_of_product')
    def _get_labour_gop_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product:
                gop_line = self.env['budget.gop.labour'].search(
                    [('budget_id', '=', res.budget_id.id), ('project_scope', '=', res.project_scope.id),
                     ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id)],
                    limit=1)
                if gop_line:
                    res.labour_gop_id = gop_line.id
                else:
                    res.labour_gop_id = False
            else:
                res.labour_gop_id = False

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('budget_id.budget_labour_ids', 'budget_id.budget_labour_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.budget_id.budget_labour_ids:
                no += 1
                l.sr_no = no

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'cs_labour_id': False,
                    'section_name': False,
                    'variable': False,
                    'group_of_product': False,
                    'product_id': False,
                    'description': False,
                })
        else:
            self.update({
                'cs_labour_id': False,
                'section_name': False,
                'variable': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'cs_labour_id': False,
                    'variable': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_labour_id': False,
                'variable': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable')
    def _onchange_variable_handling(self):
        if self._origin.variable._origin.id:
            if self._origin.variable._origin.id != self.variable.id:
                self.update({
                    'cs_labour_id': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_labour_id': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self._origin.group_of_product._origin.id:
            if self._origin.group_of_product._origin.id != self.group_of_product.id:
                self.update({
                    'cs_labour_id': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_labour_id': False,
                'product_id': False,
            })

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

    @api.onchange('time')
    def _onchange_quantity(self):
        for rec in self:
            if rec.cs_labour_id:
                if rec.time > rec.unallocated_time:
                    if rec.project_id.budgeting_method == 'gop_budget':
                        raise ValidationError("The allocated group of product amount is over the unallocated amount")
                    else:
                        raise ValidationError("The time is over the unallocated time")

    @api.depends('contractors', 'time', 'amount')
    def _amount_total_comute(self):
        for line in self:
            if (line.reserved_contractors != 0 and line.reserved_time != 0) or line.time_used != 0:
                current_contractors = line.contractors - line.reserved_contractors
                current_time = (line.time * line.contractors) - (
                            (line.reserved_time + line.time_used) * line.reserved_contractors)
                current_amount_total = current_time * line.amount

                previous_unit_price = (line.amt_res + line.amt_used + line.amount_return) / (
                            line.reserved_contractors * (line.reserved_time + line.time_used))
                previous_amount_total = (line.reserved_contractors * (
                            line.reserved_time + line.time_used)) * previous_unit_price
                line.amount_total = current_amount_total + previous_amount_total
            else:
                line.amount_total = line.contractors * line.time * line.amount

    @api.onchange('quantity', 'qty_res', 'purchased_qty')
    def _budget_quantity_left(self):
        for line in self:
            line.qty_left = line.quantity + line.carried_qty - (
                    line.reserved_time + line.purchased_qty + line.transferred_qty + line.carry_qty)

    @api.onchange('amount_total', 'amt_res', 'purchased_amt')
    def _budget_amount_left(self):
        for line in self:
            # line.amt_left = line.amount_total + line.carried_amt - (
            #         line.amt_res + line.purchased_amt + line.carry_amt + line.amount_return)
            line.amt_left = line.amount_total + line.carried_amt - (
                    line.amt_res + line.purchased_amt + line.carry_amt + line.amount_return + line.amt_used)

    # def _reserved_qty(self):
    #     for line in self:
    #         line.qty_res = line.qty_res - line.purchased_qty

    # def _reserved_amt(self):
    #    for line in self:
    #         line.amt_res = line.amt_res - line.purchased_amt

    def _unused_qty(self):
        for line in self:
            line.unused_qty = line.quantity - line.qty_used - line.dif_qty_used

    def _unused_time(self):
        for line in self:
            line.unused_time = line.time - line.time_used

    def _unused_amt(self):
        for line in self:
            line.unused_amt = line.amount_total - line.amt_used - line.dif_amt_used

    def _get_unallocated(self):
        for line in self:
            if line.cs_labour_id:
                line.unallocated_contractors = line.cs_labour_id.unallocated_contractors
                line.unallocated_time = line.cs_labour_id.unallocated_budget_time
                line.unallocated_quantity = line.cs_labour_id.product_qty_na
                line.unallocated_amount = line.cs_labour_id.product_amt_na
            else:
                line.unallocated_contractors = 0
                line.unallocated_time = 0
                line.unallocated_quantity = 0
                line.unallocated_amount = 0

    @api.onchange('date')
    def _onchange_domain_gop(self):
        for rec in self:
            cost_sheet = rec.budget_id.cost_sheet
            cs_gop = cost_sheet.material_labour_ids.mapped('group_of_product')

            return {'domain': {'group_of_product': [('id', 'in', cs_gop.ids)]}}

    @api.onchange('group_of_product')
    def _onchange_domain_product(self):
        for rec in self:
            cost_sheet = rec.budget_id.cost_sheet
            cs_product = cost_sheet.material_labour_ids.mapped('product_id')

            return {'domain': {'product_id': [('id', 'in', cs_product.ids),
                                              ('group_of_product', '=', rec.group_of_product.id)]}}

    @api.onchange('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _onchange_set_cost_sheet_line(self):
        for rec in self:
            if rec.project_scope and rec.section_name and rec.group_of_product and rec.product_id:
                cost_sheet_line = rec.env['material.labour'].search([
                    ('job_sheet_id', '=', rec.budget_id.cost_sheet.id),
                    ('project_scope', '=', rec.project_scope.id),
                    ('section_name', '=', rec.section_name.id),
                    ('group_of_product', '=', rec.group_of_product.id),
                    ('product_id', '=', rec.product_id.id)])
                if cost_sheet_line:
                    rec.update({
                        'cs_labour_id': cost_sheet_line.id,
                        'description': cost_sheet_line.description,
                        'uom_id': cost_sheet_line.uom_id.id,
                        'time': cost_sheet_line.time,
                        'contractors': cost_sheet_line.contractors,
                        'budget_quantity': cost_sheet_line.product_qty,
                        'amount': cost_sheet_line.price_unit,
                        'budget_amount': cost_sheet_line.labour_amount_total,
                        'unallocated_contractors': cost_sheet_line.unallocated_contractors,
                        'unallocated_time': cost_sheet_line.unallocated_budget_time,
                        'unallocated_quantity': cost_sheet_line.product_qty_na,
                        'unallocated_amount': cost_sheet_line.product_amt_na,
                    })
                else:
                    raise ValidationError("There is no cost sheet line for this combination, please select another "
                                          "combination!")

    def _get_id_from_cs(self):
        value = False
        for line in self:
            value = self.env['material.labour'].search([('job_sheet_id', '=', line.budget_id.cost_sheet.id),
                                                        ('project_scope', '=', line.project_scope.id),
                                                        ('section_name', '=', line.section_name.id),
                                                        ('group_of_product', '=', line.group_of_product.id),
                                                        ('product_id', '=', line.product_id.id)])
            line.cs_labour_id = value


class BudgetSubcon(models.Model):
    _name = 'budget.subcon'
    _description = "Budget Subcon"
    _order = 'sequence'
    _check_company_auto = True
    _rec_name = 'subcon_id'

    budget_id = fields.Many2one('project.budget', string='Budget')
    cs_subcon_id = fields.Many2one('material.subcon', 'Subcon ID')
    budget_carry_over_id = fields.Many2one('project.budget.carry', string="Budget Carry Over")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable',
                                   check_company=True)
    subcon_id = fields.Many2one('variable.template', string='Job Subcon',
                                check_company=True, required=True)
    description = fields.Text('Description')
    billed_qty = fields.Float('Billed Quantity', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    purchased_qty = fields.Float('Purchased Quantity', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    quantity = fields.Float(string="Budget Quantity", default=0)
    qty_left = fields.Float(string='Budget Quantity Left', compute="_budget_quantity_left")
    qty_res = fields.Float(string='Reserved Budget Quantity')
    qty_used = fields.Float('Actual Used Quantity', default=0.00)
    budget_quantity = fields.Float(string="Sheet Budget Quantity")
    unallocated_quantity = fields.Float(string="Unallocated Budget Quantity")
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    amount = fields.Float(string="Unit Price", default=0.00)
    amount_total = fields.Float(string="Budget Amount", compute="_amount_total_comute")
    amt_left = fields.Float(string='Budget Amount Left', compute="_budget_amount_left")
    amt_res = fields.Float(string='Reserved Budget Amount')
    amt_used = fields.Float('Actual Used Amount', default=0.00)
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    dif_qty_used = fields.Float('Actual Used Quantity on different budget', default=0.00)
    dif_amt_used = fields.Float('Actual Used Amount on different budget', default=0.00)
    budget_amount = fields.Float(string="Sheet Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Budget Amount")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    # Carry Over
    carried_qty = fields.Float('Carried Quantity (receive)', default=0.00)
    carried_amt = fields.Float('Carried Amount (receive)', default=0.00)
    carry_qty = fields.Float('Carried Quantity (send)', default=0.00)
    carry_amt = fields.Float('Carried Amount (send)', default=0.00)
    status = fields.Selection([('carry_to', ' Carried to'),
                               ('carry_from', 'Carried From'),
                               ('carried_over', 'Carried Over')],
                              string="Status")
    carried_to = fields.Many2one('project.budget', string='Carried To')
    carried_from = fields.Many2one('project.budget', string='Carried From')
    project_id = fields.Many2one(related='budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    amount_return = fields.Float('Return Amount', default=0.00)
    reserved_return_amount = fields.Float('Reserved Return Amount', default=0.00)
    over_amount = fields.Float('Over Amount', default=0.00)
    reserved_over_amount = fields.Float('Reserved Over Amount', default=0.00)
    po_reserved_qty = fields.Float('PO Reserved Quantity', default=0.00)

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('budget_id.budget_subcon_ids', 'budget_id.budget_subcon_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.budget_id.budget_subcon_ids:
                no += 1
                l.sr_no = no

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'cs_subcon_id': False,
                    'section_name': False,
                    'subcon_id': False,
                    'description': False,
                })
        else:
            self.update({
                'cs_subcon_id': False,
                'section_name': False,
                'subcon_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'cs_subcon_id': False,
                    'subcon_id': False,
                })
        else:
            self.update({
                'cs_subcon_id': False,
                'subcon_id': False,
            })

    @api.onchange('subcon_id')
    def onchange_product_id(self):
        if self.subcon_id:
            self.uom_id = self.subcon_id.variable_uom.id
            self.quantity = 1.0
            self.description = self.subcon_id.name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = False

    @api.onchange('quantity')
    def _onchange_quantity(self):
        for rec in self:
            if rec.cs_subcon_id:
                if rec.quantity > rec.unallocated_quantity:
                    raise ValidationError("The quantity is over the unallocated quantity")

    @api.onchange('quantity', 'amount')
    def _amount_total_comute(self):
        for line in self:
            # line.amount_total = line.quantity * line.amount
            if (line.qty_res > 0 and line.amt_res) or line.purchased_qty > 0:
                current_quantity = line.quantity - line.qty_res - line.purchased_qty
                current_amount_total = current_quantity * line.amount
                if line.qty_res > 0 >= line.po_reserved_qty:
                    previous_unit_price = ((line.amt_res + line.purchased_amt + line.amount_return
                                            + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.qty_res + line.purchased_qty))
                else:
                    previous_unit_price = ((line.amt_res + line.purchased_amt + line.amount_return
                                            + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.po_reserved_qty + line.purchased_qty))
                previous_amount_total = previous_unit_price * (line.purchased_qty + line.qty_res)
                line.amount_total = current_amount_total + previous_amount_total
            else:
                line.amount_total = line.quantity * line.amount

    @api.onchange('quantity', 'qty_res', 'purchased_qty')
    def _budget_quantity_left(self):
        for line in self:
            line.qty_left = line.quantity + line.carried_qty - (line.qty_res + line.purchased_qty + line.carry_qty)

    @api.onchange('amount_total', 'amt_res', 'purchased_amt')
    def _budget_amount_left(self):
        for line in self:
            line.amt_left = line.amount_total + line.carried_amt - (line.amt_res + line.purchased_amt + line.carry_amt
                                                                    + line.amount_return)

    # def _reserved_qty(self):
    #     for line in self:
    #         line.qty_res = line.qty_res - line.purchased_qty

    # def _reserved_amt(self):
    #    for line in self:
    #         line.amt_res = line.amt_res - line.purchased_amt

    def _unused_qty(self):
        for line in self:
            line.unused_qty = line.quantity - line.qty_used - line.dif_qty_used

    def _unused_amt(self):
        for line in self:
            line.unused_amt = line.amount_total - line.amt_used - line.dif_amt_used

    def _get_unallocated(self):
        for line in self:
            if line.cs_subcon_id:
                line.unallocated_quantity = line.cs_subcon_id.product_qty_na
                line.unallocated_amount = line.cs_subcon_id.product_amt_na
            else:
                line.unallocated_quantity = 0
                line.unallocated_amount = 0

    @api.onchange('date')
    def _onchange_domain_gop(self):
        for rec in self:
            cost_sheet = rec.budget_id.cost_sheet
            cs_subcon = cost_sheet.material_subcon_ids.mapped('variable')

            return {'domain': {'subcon_id': [('id', 'in', cs_subcon.ids)]}}

    @api.onchange('project_scope', 'section_name', 'subcon_id')
    def _onchange_set_cost_sheet_line(self):
        for rec in self:
            if rec.project_scope and rec.section_name and rec.subcon_id:
                cost_sheet_line = rec.env['material.subcon'].search([
                    ('job_sheet_id', '=', rec.budget_id.cost_sheet.id),
                    ('project_scope', '=', rec.project_scope.id),
                    ('section_name', '=', rec.section_name.id),
                    ('variable', '=', rec.subcon_id.id)])
                if cost_sheet_line:
                    rec.update({
                        'cs_subcon_id': cost_sheet_line.id,
                        'description': cost_sheet_line.description,
                        'uom_id': cost_sheet_line.uom_id.id,
                        'budget_quantity': cost_sheet_line.product_qty,
                        'amount': cost_sheet_line.price_unit,
                        'budget_amount': cost_sheet_line.subcon_amount_total,
                        'unallocated_quantity': cost_sheet_line.product_qty_na,
                        'unallocated_amount': cost_sheet_line.product_amt_na,
                    })
                else:
                    raise ValidationError("There is no cost sheet line for this combination, please select another "
                                          "combination!")

    def _get_id_from_cs(self):
        value = False
        for line in self:
            value = self.env['material.subcon'].search([('job_sheet_id', '=', line.budget_id.cost_sheet.id),
                                                        ('project_scope', '=', line.project_scope.id),
                                                        ('section_name', '=', line.section_name.id),
                                                        ('variable', '=', line.subcon_id.id)])
            line.cs_subcon_id = value


class BudgetOverhead(models.Model):
    _name = 'budget.overhead'
    _description = "Budget Overhead"
    _order = 'sequence'
    _check_company_auto = True

    name = fields.Char('name', compute='_compute_name')
    budget_id = fields.Many2one('project.budget', string='Budget')
    cs_overhead_id = fields.Many2one('material.overhead', 'Overhead ID')
    budget_carry_over_id = fields.Many2one('project.budget.carry', string="Budget Carry Over")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product',
                                 check_company=True, required=True)
    description = fields.Text('Description')
    billed_qty = fields.Float('Billed Quantity', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    purchased_qty = fields.Float('Purchased Quantity', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    quantity = fields.Float(string="Budget Quantity", default=0)
    qty_left = fields.Float(string='Budget Quantity Left', compute="_budget_quantity_left")
    qty_res = fields.Float(string='Budget Quantity Reserved')
    qty_used = fields.Float('Actual Used Quantity', default=0.00)
    transferred_qty = fields.Float('Transferred Quantity')
    transferred_amt = fields.Float('Transferred Amount')
    qty_received = fields.Float('Received Quantity')
    budget_quantity = fields.Float(string="Sheet Budget Quantity")
    unallocated_quantity = fields.Float(string="Unallocated Budget Quantity")
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    amount = fields.Float(string="Unit Price", default=0.00)
    amount_total = fields.Float(string="Budget Amount", compute="_amount_total_comute")
    amt_left = fields.Float(string='Budget Amount Left', compute="_budget_amount_left")
    amt_res = fields.Float(string='Reserved Budget Amount')
    amt_used = fields.Float('Actual Used Amount', default=0.00)
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    dif_qty_used = fields.Float('Actual Used Quantity on different budget', default=0.00)
    dif_amt_used = fields.Float('Actual Used Amount on different budget', default=0.00)
    budget_amount = fields.Float(string="Sheet Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Budget Amount")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    on_hand_qty = fields.Float(string='On Hand Quantity', related='cs_overhead_id.on_hand_qty')
    on_hand_qty_converted = fields.Float(related='cs_overhead_id.on_hand_qty_converted')
    overhead_catagory = fields.Selection([
        ('product', 'Product'),
        ('petty cash', 'Petty Cash'),
        ('cash advance', 'Cash Advance'),
        ('fuel', 'Fuel'),
    ], string='Overhead Catagory', required=True)
    # Carry Over
    carried_qty = fields.Float('Carried Quantity (receive)', default=0.00)
    carried_amt = fields.Float('Carried Amount (receive)', default=0.00)
    carry_qty = fields.Float('Carried Quantity (send)', default=0.00)
    carry_amt = fields.Float('Carried Amount (send)', default=0.00)
    status = fields.Selection([('carry_to', ' Carried to'),
                               ('carry_from', 'Carried From'),
                               ('carried_over', 'Carried Over')],
                              string="Status")
    carried_to = fields.Many2one('project.budget', string='Carried To')
    carried_from = fields.Many2one('project.budget', string='Carried From')
    project_id = fields.Many2one(related='budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    overhead_gop_id = fields.Many2one('budget.gop.overhead', string="Ovehead GOP ID", compute="_get_overhead_gop_id")
    amount_return = fields.Float('Return Amount', default=0.00)
    reserved_return_amount = fields.Float('Reserved Return Amount', default=0.00)
    over_amount = fields.Float('Over Amount', default=0.00)
    reserved_over_amount = fields.Float('Reserved Over Amount', default=0.00)
    po_reserved_qty = fields.Float('PO Reserved Quantity', default=0.00)

    @api.depends('project_scope', 'section_name', 'group_of_product')
    def _get_overhead_gop_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product:
                gop_line = self.env['budget.gop.overhead'].search(
                    [('budget_id', '=', res.budget_id.id), ('project_scope', '=', res.project_scope.id),
                     ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id)],
                    limit=1)
                if gop_line:
                    res.overhead_gop_id = gop_line.id
                else:
                    res.overhead_gop_id = False
            else:
                res.overhead_gop_id = False

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('name')
    def _compute_name(self):
        record = False
        for rec in self:
            scope = rec.project_scope.name
            section = rec.section_name.name
            variable = rec.variable.name
            product = rec.product_id.name
            if rec.project_scope and rec.section_name and rec.variable and rec.product_id:
                record = scope + ' - ' + section + ' - ' + variable + ' - ' + product
            elif rec.project_scope and rec.section_name and rec.product_id:
                record = scope + ' - ' + section + ' - ' + product
            rec.write({'name': record})

    @api.depends('budget_id.budget_overhead_ids', 'budget_id.budget_overhead_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.budget_id.budget_overhead_ids:
                no += 1
                l.sr_no = no

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'cs_overhead_id': False,
                    'section_name': False,
                    'variable': False,
                    'group_of_product': False,
                    'product_id': False,
                    'description': False,
                })
        else:
            self.update({
                'cs_overhead_id': False,
                'section_name': False,
                'variable': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'cs_overhead_id': False,
                    'variable': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_overhead_id': False,
                'variable': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable')
    def _onchange_variable_handling(self):
        if self._origin.variable._origin.id:
            if self._origin.variable._origin.id != self.variable.id:
                self.update({
                    'cs_overhead_id': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_overhead_id': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self._origin.group_of_product._origin.id:
            if self._origin.group_of_product._origin.id != self.group_of_product.id:
                self.update({
                    'cs_overhead_id': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_overhead_id': False,
                'product_id': False,
            })

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

    @api.onchange('quantity')
    def _onchange_quantity(self):
        for rec in self:
            if rec.cs_overhead_id:
                if rec.quantity > rec.unallocated_quantity:
                    if rec.project_id.budgeting_method == 'gop_budget':
                        raise ValidationError("The allocated group of product amount is over the unallocated amount")
                    else:
                        raise ValidationError("The quantity is over the unallocated quantity")

    @api.onchange('quantity', 'amount')
    def _amount_total_comute(self):
        for line in self:
            # line.amount_total = line.quantity * line.amount
            if (line.qty_res > 0 and line.amt_res) or line.purchased_qty > 0 or (line.transferred_qty and line.transferred_amt):
                current_quantity = line.quantity - line.qty_res - line.purchased_qty - line.transferred_qty
                current_amount_total = current_quantity * line.amount
                if line.qty_res > 0 >= line.po_reserved_qty:
                    previous_unit_price = ((line.amt_res + line.purchased_amt + line.amount_return
                                            + line.transferred_amt + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.qty_res + line.purchased_qty + line.transferred_qty))
                else:
                    previous_unit_price = ((line.amt_res + line.purchased_amt + line.amount_return
                                            + line.transferred_amt + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.po_reserved_qty + line.purchased_qty + line.transferred_qty))
                previous_amount_total = previous_unit_price * (line.purchased_qty + line.qty_res + line.transferred_qty)
                line.amount_total = current_amount_total + previous_amount_total
            else:
                line.amount_total = line.quantity * line.amount

    @api.onchange('quantity', 'qty_res', 'purchased_qty')
    def _budget_quantity_left(self):
        for line in self:
            line.qty_left = line.quantity + line.carried_qty - (
                    line.qty_res + line.purchased_qty + line.transferred_qty + line.carry_qty)

    @api.onchange('amount_total', 'amt_res', 'purchased_amt')
    def _budget_amount_left(self):
        for line in self:
            line.amt_left = line.amount_total + line.carried_amt - (
                    line.amt_res + line.purchased_amt + line.carry_amt + line.amount_return + line.transferred_amt)

    # def _reserved_qty(self):
    #     for line in self:
    #         line.qty_res = line.qty_res - line.purchased_qty

    # def _reserved_amt(self):
    #    for line in self:
    #         line.amt_res = line.amt_res - line.purchased_amt

    def _unused_qty(self):
        for line in self:
            line.unused_qty = line.quantity - line.qty_used - line.dif_qty_used

    def _unused_amt(self):
        for line in self:
            line.unused_amt = line.amount_total - line.amt_used - line.dif_amt_used

    def _get_unallocated(self):
        for line in self:
            if line.cs_overhead_id:
                line.unallocated_quantity = line.cs_overhead_id.product_qty_na
                line.unallocated_amount = line.cs_overhead_id.product_amt_na
            else:
                line.unallocated_quantity = 0
                line.unallocated_amount = 0

    @api.onchange('date')
    def _onchange_domain_gop(self):
        for rec in self:
            cost_sheet = rec.budget_id.cost_sheet
            cs_gop = cost_sheet.material_overhead_ids.mapped('group_of_product')

            return {'domain': {'group_of_product': [('id', 'in', cs_gop.ids)]}}

    @api.onchange('group_of_product', 'overhead_catagory')
    def _onchange_domain_product(self):
        for rec in self:
            cost_sheet = rec.budget_id.cost_sheet
            cs_product = cost_sheet.material_overhead_ids.mapped('product_id')
            if rec.overhead_catagory in ('product', 'fuel'):
                return {'domain': {'product_id': [('id', 'in', cs_product.ids),
                                                  ('group_of_product', '=', rec.group_of_product.id),
                                                  ('type', '=', 'product')]}}
            else:
                return {'domain': {'product_id': [('id', 'in', cs_product.ids),
                                                  ('group_of_product', '=', rec.group_of_product.id),
                                                  ('type', '=', 'consu')]}}

    @api.onchange('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _onchange_set_cost_sheet_line(self):
        for rec in self:
            if rec.project_scope and rec.section_name and rec.group_of_product and rec.product_id:
                cost_sheet_line = rec.env['material.overhead'].search([
                    ('job_sheet_id', '=', rec.budget_id.cost_sheet.id),
                    ('project_scope', '=', rec.project_scope.id),
                    ('section_name', '=', rec.section_name.id),
                    ('group_of_product', '=', rec.group_of_product.id),
                    ('product_id', '=', rec.product_id.id)])
                if cost_sheet_line:
                    rec.update({
                        'cs_overhead_id': cost_sheet_line.id,
                        'description': cost_sheet_line.description,
                        'uom_id': cost_sheet_line.uom_id.id,
                        'budget_quantity': cost_sheet_line.product_qty,
                        'amount': cost_sheet_line.price_unit,
                        'budget_amount': cost_sheet_line.overhead_amount_total,
                        'unallocated_quantity': cost_sheet_line.product_qty_na,
                        'unallocated_amount': cost_sheet_line.product_amt_na,
                    })
                else:
                    raise ValidationError("There is no cost sheet line for this combination, please select another "
                                          "combination!")

    def _get_id_from_cs(self):
        value = False
        for line in self:
            value = self.env['material.overhead'].search([('job_sheet_id', '=', line.budget_id.cost_sheet.id),
                                                          ('project_scope', '=', line.project_scope.id),
                                                          ('section_name', '=', line.section_name.id),
                                                          ('group_of_product', '=', line.group_of_product.id),
                                                          ('product_id', '=', line.product_id.id)])
            line.cs_overhead_id = value


# --- newly added 'budget Internal asset' object -----
class BudgetInternalAsset(models.Model):
    _name = 'budget.internal.asset'
    _description = "Internal Asset"
    _order = 'sequence'

    name = fields.Char('name', compute='_compute_name')
    project_budget_id = fields.Many2one('project.budget', string='Project Budget')
    cs_internal_asset_id = fields.Many2one('internal.asset', 'Internal Asset ID')
    budget_carry_over_id = fields.Many2one('project.budget.carry', string="Budget Carry Over")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope_line_id = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_id = fields.Many2one('variable.template', string='Variable')
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category', required=True)
    asset_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    budgeted_qty = fields.Float('Budget Quantity', default=0.00, required=True)
    unallocated_budget_qty = fields.Float('Unallocated Budget Quantity', default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    price_unit = fields.Float(string='Unit Price', default=0.00, required=True)
    budgeted_amt = fields.Float('Budget Amount', default=0.00, compute="_budgeted_amt", force_save="1")
    unallocated_budget_amt = fields.Float('Unallocated Budget Ammount', default=0.00)
    budgeted_qty_left = fields.Float('Budgeted Quantity Left', compute="_budget_quntity_left", force_save="1")
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left", force_save="1")
    actual_used_qty = fields.Float('Actual Used Quantity', default=0.00)
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    dif_qty_used = fields.Float('Actual Used Quantity on different budget', default=0.00)
    dif_amt_used = fields.Float('Actual Used Amount on different budget', default=0.00)
    # Carry Over
    carried_qty = fields.Float('Carried Quantity (receive)', default=0.00)
    carried_amt = fields.Float('Carried Amount (receive)', default=0.00)
    carry_qty = fields.Float('Carried Quantity (send)', default=0.00)
    carry_amt = fields.Float('Carried Amount (send)', default=0.00)
    status = fields.Selection([('carry_to', ' Carried to'),
                               ('carry_from', 'Carried From'),
                               ('carried_over', 'Carried Over')],
                              string="Status")
    carried_to = fields.Many2one('project.budget', string='Carried To')
    carried_from = fields.Many2one('project.budget', string='Carried From')
    project_id = fields.Many2one(related='project_budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')

    @api.depends('project_id.project_section_ids', 'project_scope_line_id')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope_line_id:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope_line_id.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('name')
    def _compute_name(self):
        record = False
        for rec in self:
            scope = rec.project_scope_line_id.name
            section = rec.section_name.name
            variable = rec.variable_id.name
            asset = rec.asset_id.name
            if rec.project_scope_line_id and rec.section_name and rec.variable_id and rec.asset_id:
                record = scope + ' - ' + section + ' - ' + variable + ' - ' + asset
            elif rec.project_scope_line_id and rec.section_name and rec.asset_id:
                record = scope + ' - ' + section + ' - ' + asset
            rec.write({'name': record})

    @api.onchange('asset_category_id')
    def onchange_asset_category(self):
        if self.asset_category_id:
            asset = self.env['maintenance.equipment'].sudo().search(
                [('category_id.id', '=', self.asset_category_id.id)])
            return {'domain': {'asset_id': [('id', 'in', asset.ids)]}}

    @api.depends('project_budget_id.budget_internal_asset_ids', 'project_budget_id.budget_internal_asset_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.budget_internal_asset_ids:
                no += 1
                l.sr_no = no

    @api.onchange('project_scope_line_id')
    def _onchange_project_scope_line_id_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope_line_id._origin.id:
            if self._origin.project_scope_line_id._origin.id != self.project_scope_line_id.id:
                self.update({
                    'cs_internal_asset_id': False,
                    'section_name': False,
                    'asset_category_id': False,
                    'asset_id': False,
                })
        else:
            self.update({
                'cs_internal_asset_id': False,
                'section_name': False,
                'asset_category_id': False,
                'asset_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'cs_internal_asset_id': False,
                    'asset_category_id': False,
                    'asset_id': False,
                })
        else:
            self.update({
                'cs_internal_asset_id': False,
                'asset_category_id': False,
                'asset_id': False,
            })

    @api.onchange('asset_category_id')
    def _onchange_asset_category_id_handling(self):
        if self._origin.asset_category_id._origin.id:
            if self._origin.asset_category_id._origin.id != self.asset_category_id.id:
                self.update({
                    'cs_internal_asset_id': False,
                    'asset_id': False,
                })
        else:
            self.update({
                'cs_internal_asset_id': False,
                'asset_id': False,
            })

    @api.onchange('asset_id')
    def onchange_asset_id(self):
        if self.asset_id:
            self.budgeted_qty = 1.0
        else:
            self.budgeted_qty = 1.0

    def _get_unallocated(self):
        for line in self:
            if line.cs_internal_asset_id:
                line.unallocated_budget_qty = line.cs_internal_asset_id.unallocated_budget_qty
                line.unallocated_budget_amt = line.cs_internal_asset_id.unallocated_amt
            else:
                line.unallocated_budget_qty = 0
                line.unallocated_budget_amt = 0

    @api.onchange('budgeted_qty')
    def _onchange_quantity(self):
        for rec in self:
            if rec.cs_internal_asset_id:
                if rec.budgeted_qty > rec.unallocated_budget_qty:
                    raise ValidationError("The quantity is over the unallocated quantity")

    @api.depends('budgeted_qty', 'price_unit')
    def _budgeted_amt(self):
        for rec in self:
            if rec.actual_used_amt != 0:
                current_quantity = rec.budgeted_qty - rec.actual_used_qty
                current_amount_total = current_quantity * rec.price_unit
                previous_unit_price = rec.actual_used_amt / rec.actual_used_qty
                previous_amount_total = previous_unit_price * rec.actual_used_qty
                rec.budgeted_amt = current_amount_total + previous_amount_total
            else:
                rec.budgeted_amt = rec.budgeted_qty * rec.price_unit

    @api.depends('budgeted_qty', 'actual_used_qty')
    def _budget_quntity_left(self):
        for rec in self:
            budget_qty = rec.budgeted_qty
            actual_used_qty = rec.actual_used_qty
            carried_amt = rec.carried_amt
            carry_amt = rec.carry_amt
            rec.budgeted_qty_left = budget_qty + carried_amt - actual_used_qty - carry_amt

    @api.depends('budgeted_amt', 'actual_used_amt')
    def _budget_amount_left(self):
        for rec in self:
            budget_amt = rec.budgeted_amt
            actual_used_amt = rec.actual_used_amt
            carried_amt = rec.carried_amt
            carry_amt = rec.carry_amt
            rec.budgeted_amt_left = budget_amt + carried_amt - actual_used_amt - carry_amt

    @api.onchange('date')
    def _onchange_domain_gop(self):
        for rec in self:
            cost_sheet = rec.project_budget_id.cost_sheet
            cs_category = cost_sheet.internal_asset_ids.mapped('asset_category_id')

            return {'domain': {'asset_category_id': [('id', 'in', cs_category.ids)]}}

    @api.onchange('asset_category_id')
    def _onchange_domain_product(self):
        for rec in self:
            cost_sheet = rec.project_budget_id.cost_sheet
            cs_asset = cost_sheet.internal_asset_ids.mapped('asset_id')

            return {'domain': {'asset_id': [('id', 'in', cs_asset.ids),
                                            ('category_id', '=', rec.asset_category_id.id)]}}

    @api.onchange('project_scope_line_id', 'section_name', 'asset_category_id', 'asset_id')
    def _onchange_set_cost_sheet_line(self):
        for rec in self:
            if rec.project_scope_line_id and rec.section_name and rec.asset_category_id and rec.asset_id:
                cost_sheet_line = rec.env['internal.asset'].search([
                    ('job_sheet_id', '=', rec.project_budget_id.cost_sheet.id),
                    ('project_scope', '=', rec.project_scope_line_id.id),
                    ('section_name', '=', rec.section_name.id),
                    ('asset_category_id', '=', rec.asset_category_id.id),
                    ('asset_id', '=', rec.asset_id.id)])
                if cost_sheet_line:
                    rec.update({
                        'cs_internal_asset_id': cost_sheet_line.id,
                        'asset_category_id': cost_sheet_line.asset_category_id.id,
                        'asset_id': cost_sheet_line.asset_id.id,
                        'uom_id': cost_sheet_line.uom_id.id,
                        'budgeted_qty': cost_sheet_line.budgeted_qty,
                        'price_unit': cost_sheet_line.price_unit,
                        'budgeted_amt': cost_sheet_line.budgeted_amt,
                        'unallocated_budget_qty': cost_sheet_line.unallocated_budget_qty,
                        'unallocated_budget_amt': cost_sheet_line.unallocated_amt,
                    })
                else:
                    raise ValidationError("There is no cost sheet line for this combination, please select another "
                                          "combination!")

    def _get_id_from_cs(self):
        value = False
        for line in self:
            value = self.env['internal.asset'].search([('job_sheet_id', '=', line.budget_id.cost_sheet.id),
                                                       ('project_scope', '=', line.project_scope.id),
                                                       ('section_name', '=', line.section_name.id),
                                                       ('asset_category_id', '=', line.asset_category_id.id),
                                                       ('asset_id', '=', line.asset_id.id)])
            line.cs_overhead_id = value


class BudgetEquipment(models.Model):
    _name = 'budget.equipment'
    _description = "Budget Equipment"
    _order = 'sequence'
    _check_company_auto = True

    budget_id = fields.Many2one('project.budget', string='Budget')
    cs_equipment_id = fields.Many2one('material.equipment', 'Equipment ID')
    budget_carry_over_id = fields.Many2one('project.budget.carry', string="Budget Carry Over")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string='Product',
                                 check_company=True, required=True)
    description = fields.Text('Description')
    billed_qty = fields.Float('Billed Quantity', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    purchased_qty = fields.Float('Purchased Quantity', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    quantity = fields.Float(string="Budget Quantity", default=0)
    qty_left = fields.Float(string='Budget Quantity Left', compute="_budget_quantity_left")
    qty_res = fields.Float(string='Reserved Budget Quantity')
    qty_used = fields.Float('Actual Used Quantity', default=0.00)
    qty_received = fields.Float('Received Quantity')
    qty_returned = fields.Float('Returned Quantity')
    budget_quantity = fields.Float(string="Sheet Budget Quantity")
    unallocated_quantity = fields.Float(string="Unallocated Budget Quantity")
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    amount = fields.Float(string="Unit Price", default=0.00)
    amount_total = fields.Float(string="Budget Amount", compute="_amount_total_comute")
    amt_left = fields.Float(string='Budget Amount Left', compute="_budget_amount_left")
    amt_res = fields.Float(string='Reserved Budget Amount')
    amt_used = fields.Float('Actual Used Amount', default=0.00)
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    dif_qty_used = fields.Float('Actual Used Quantity on different budget', default=0.00)
    dif_amt_used = fields.Float('Actual Used Amount on different budget', default=0.00)
    budget_amount = fields.Float(string="Sheet Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Budget Amount")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    # Carry Over
    carried_qty = fields.Float('Carried Quantity (receive)', default=0.00)
    carried_amt = fields.Float('Carried Amount (receive)', default=0.00)
    carry_qty = fields.Float('Carried Quantity (send)', default=0.00)
    carry_amt = fields.Float('Carried Amount (send)', default=0.00)
    status = fields.Selection([('carry_to', ' Carried to'),
                               ('carry_from', 'Carried From'),
                               ('carried_over', 'Carried Over')],
                              string="Status")
    carried_to = fields.Many2one('project.budget', string='Carried To')
    carried_from = fields.Many2one('project.budget', string='Carried From')
    project_id = fields.Many2one(related='budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    equipment_gop_id = fields.Many2one('material.gop.equipment', string="Equipment GOP ID",
                                       compute="_get_equipment_gop_id")
    amount_return = fields.Float('Return Amount', default=0.00)
    reserved_return_amount = fields.Float('Reserved Return Amount', default=0.00)
    over_amount = fields.Float('Over Amount', default=0.00)
    reserved_over_amount = fields.Float('Reserved Over Amount', default=0.00)
    po_reserved_qty = fields.Float('PO Reserved Quantity', default=0.00)

    @api.depends('project_scope', 'section_name', 'group_of_product')
    def _get_equipment_gop_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product:
                gop_line = self.env['budget.gop.equipment'].search(
                    [('budget_id', '=', res.budget_id.id), ('project_scope', '=', res.project_scope.id),
                     ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id)],
                    limit=1)
                if gop_line:
                    res.equipment_gop_id = gop_line.id
                else:
                    res.equipment_gop_id = False
            else:
                res.equipment_gop_id = False

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('budget_id.budget_equipment_ids', 'budget_id.budget_equipment_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.budget_id.budget_equipment_ids:
                no += 1
                l.sr_no = no

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'cs_equipment_id': False,
                    'section_name': False,
                    'variable': False,
                    'group_of_product': False,
                    'product_id': False,
                    'description': False,
                })
        else:
            self.update({
                'cs_equipment_id': False,
                'section_name': False,
                'variable': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'cs_equipment_id': False,
                    'variable': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_equipment_id': False,
                'variable': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable')
    def _onchange_variable_handling(self):
        if self._origin.variable._origin.id:
            if self._origin.variable._origin.id != self.variable.id:
                self.update({
                    'cs_equipment_id': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_equipment_id': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self._origin.group_of_product._origin.id:
            if self._origin.group_of_product._origin.id != self.group_of_product.id:
                self.update({
                    'cs_equipment_id': False,
                    'product_id': False,
                })
        else:
            self.update({
                'cs_equipment_id': False,
                'product_id': False,
            })

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

    @api.onchange('quantity')
    def _onchange_quantity(self):
        for rec in self:
            if rec.cs_equipment_id:
                if rec.quantity > rec.unallocated_quantity:
                    if rec.project_id.budgeting_method == 'gop_budget':
                        raise ValidationError("The allocated group of product amount is over the unallocated amount")
                    else:
                        raise ValidationError("The quantity is over the unallocated quantity")

    @api.onchange('quantity', 'amount')
    def _amount_total_comute(self):
        for line in self:
            # line.amount_total = line.quantity * line.amount
            if (line.qty_res > 0 and line.amt_res) or line.purchased_qty > 0:
                current_quantity = line.quantity - line.qty_res - line.purchased_qty
                current_amount_total = current_quantity * line.amount
                if line.qty_res > 0 >= line.po_reserved_qty:
                    previous_unit_price = ((line.amt_res + line.purchased_amt + line.amount_return
                                            + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.qty_res + line.purchased_qty))
                else:
                    previous_unit_price = ((line.amt_res + line.purchased_amt + line.amount_return
                                            + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.po_reserved_qty + line.purchased_qty))
                previous_amount_total = previous_unit_price * (line.purchased_qty + line.qty_res)
                line.amount_total = current_amount_total + previous_amount_total
            else:
                line.amount_total = line.quantity * line.amount

    @api.onchange('quantity', 'qty_res', 'purchased_qty')
    def _budget_quantity_left(self):
        for line in self:
            line.qty_left = line.quantity + line.carried_qty - (line.qty_res + line.purchased_qty + line.carry_qty)

    @api.onchange('amount_total', 'amt_res', 'purchased_amt')
    def _budget_amount_left(self):
        for line in self:
            line.amt_left = line.amount_total + line.carried_amt - (line.amt_res + line.purchased_amt + line.carry_amt
                                                                    + line.amount_return)

    # def _reserved_qty(self):
    #     for line in self:
    #         line.qty_res = line.qty_res - line.purchased_qty

    # def _reserved_amt(self):
    #    for line in self:
    #         line.amt_res = line.amt_res - line.purchased_amt

    def _unused_qty(self):
        for line in self:
            line.unused_qty = line.quantity - line.qty_used - line.dif_qty_used

    def _unused_amt(self):
        for line in self:
            line.unused_amt = line.amount_total - line.amt_used - line.dif_amt_used

    def _get_unallocated(self):
        for line in self:
            if line.cs_equipment_id:
                line.unallocated_quantity = line.cs_equipment_id.product_qty_na
                line.unallocated_amount = line.cs_equipment_id.product_amt_na
            else:
                line.unallocated_quantity = 0
                line.unallocated_amount = 0

    @api.onchange('date')
    def _onchange_domain_gop(self):
        for rec in self:
            cost_sheet = rec.budget_id.cost_sheet
            cs_gop = cost_sheet.material_equipment_ids.mapped('group_of_product')

            return {'domain': {'group_of_product': [('id', 'in', cs_gop.ids)]}}

    @api.onchange('group_of_product')
    def _onchange_domain_product(self):
        for rec in self:
            cost_sheet = rec.budget_id.cost_sheet
            cs_product = cost_sheet.material_equipment_ids.mapped('product_id')

            return {'domain': {'product_id': [('id', 'in', cs_product.ids),
                                              ('group_of_product', '=', rec.group_of_product.id)]}}

    @api.onchange('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _onchange_set_cost_sheet_line(self):
        for rec in self:
            if rec.project_scope and rec.section_name and rec.group_of_product and rec.product_id:
                cost_sheet_line = rec.env['material.equipment'].search([
                    ('job_sheet_id', '=', rec.budget_id.cost_sheet.id),
                    ('project_scope', '=', rec.project_scope.id),
                    ('section_name', '=', rec.section_name.id),
                    ('group_of_product', '=', rec.group_of_product.id),
                    ('product_id', '=', rec.product_id.id)])
                if cost_sheet_line:
                    rec.update({
                        'cs_equipment_id': cost_sheet_line.id,
                        'description': cost_sheet_line.description,
                        'uom_id': cost_sheet_line.uom_id.id,
                        'budget_quantity': cost_sheet_line.product_qty,
                        'amount': cost_sheet_line.price_unit,
                        'budget_amount': cost_sheet_line.equipment_amount_total,
                        'unallocated_quantity': cost_sheet_line.product_qty_na,
                        'unallocated_amount': cost_sheet_line.product_amt_na,
                    })
                else:
                    raise ValidationError("There is no cost sheet line for this combination, please select another "
                                          "combination!")

    def _get_id_from_cs(self):
        value = False
        for line in self:
            value = self.env['material.equipment'].search([('job_sheet_id', '=', line.budget_id.cost_sheet.id),
                                                           ('project_scope', '=', line.project_scope.id),
                                                           ('section_name', '=', line.section_name.id),
                                                           ('group_of_product', '=', line.group_of_product.id),
                                                           ('product_id', '=', line.product_id.id)])
            line.cs_equipment_id = value


class BudgetGopMaterial(models.Model):
    _name = 'budget.gop.material'
    _description = "Bugdet Material Gop"
    _order = 'sequence'

    budget_id = fields.Many2one('project.budget', string='Budget')
    cs_material_gop_id = fields.Many2one('material.gop.material', 'Material GOP ID')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    billed_amt = fields.Float('Billed Amount', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    transferred_amt = fields.Float('Transferred Amount')
    amount_total = fields.Float(string="Budget Amount")
    amt_left = fields.Float(string='Budget Amount Left', compute="_budget_amount_left")
    amt_res = fields.Float(string='Reserved Budget Amount')
    amt_used = fields.Float('Actual Used Amount', default=0.00)
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    dif_amt_used = fields.Float('Actual Used Amount on different budget', default=0.00)
    budget_amount = fields.Float(string="Sheet Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Budget Amount")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='budget_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    # Carry Over
    carried_amt = fields.Float('Carried Amount (receive)', default=0.00)
    carry_amt = fields.Float('Carried Amount (send)', default=0.00)
    status = fields.Selection([('carry', ' Carry Over')],
                              string="Status")
    carried_to = fields.Many2one('project.budget', string='Carried To')
    carried_from = fields.Many2one('project.budget', string='Carried From')
    carried_over = fields.Boolean(string='Carried Over')
    project_id = fields.Many2one(related='budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    amount_return = fields.Float('Return Amount', default=0.00)

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('budget_id.budget_material_gop_ids', 'budget_id.budget_material_gop_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.budget_id.budget_material_gop_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('amount_total', 'amt_res', 'purchased_amt')
    def _budget_amount_left(self):
        for line in self:
            line.amt_left = line.amount_total + line.carried_amt - (
                    line.amt_res + line.purchased_amt  + line.carry_amt + line.amount_return + line.transferred_amt)

    def _unused_amt(self):
        for line in self:
            line.unused_amt = line.amount_total - line.amt_used - line.dif_amt_used

    def _get_unallocated(self):
        for line in self:
            if line.cs_material_gop_id:
                line.unallocated_amount = line.cs_material_gop_id.product_amt_na
            else:
                line.unallocated_amount = 0


class BudgetGopLabour(models.Model):
    _name = 'budget.gop.labour'
    _description = "Bugdet labour Gop"
    _order = 'sequence'

    budget_id = fields.Many2one('project.budget', string='Budget')
    cs_labour_gop_id = fields.Many2one('material.gop.labour', 'Labour GOP ID')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    billed_amt = fields.Float('Billed Amount', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    transferred_amt = fields.Float('Transferred Amount')
    amount_total = fields.Float(string="Budget Amount")
    amt_left = fields.Float(string='Budget Amount Left', compute="_budget_amount_left")
    amt_res = fields.Float(string='Reserved Budget Amount')
    amt_used = fields.Float('Actual Used Amount', default=0.00)
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    dif_amt_used = fields.Float('Actual Used Amount on different budget', default=0.00)
    budget_amount = fields.Float(string="Sheet Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Budget Amount")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='budget_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    # Carry Over
    carried_amt = fields.Float('Carried Amount (receive)', default=0.00)
    carry_amt = fields.Float('Carried Amount (send)', default=0.00)
    status = fields.Selection([('carry', ' Carry Over')],
                              string="Status")
    carried_to = fields.Many2one('project.budget', string='Carried To')
    carried_from = fields.Many2one('project.budget', string='Carried From')
    carried_over = fields.Boolean(string='Carried Over')
    project_id = fields.Many2one(related='budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    amount_return = fields.Float('Return Amount', default=0.00)

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('budget_id.budget_labour_gop_ids', 'budget_id.budget_labour_gop_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.budget_id.budget_labour_gop_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('amount_total', 'amt_res', 'purchased_amt')
    def _budget_amount_left(self):
        for line in self:
            # line.amt_left = line.amount_total + line.carried_amt - (
            #         line.amt_res + line.purchased_amt + line.carry_amt + line.amount_return)
            line.amt_left = line.amount_total + line.carried_amt - (
                    line.amt_res + line.purchased_amt + line.carry_amt + line.amount_return + line.amt_used)

    def _unused_amt(self):
        for line in self:
            line.unused_amt = line.amount_total - line.amt_used - line.dif_amt_used

    def _get_unallocated(self):
        for line in self:
            if line.cs_labour_gop_id:
                line.unallocated_amount = line.cs_labour_gop_id.product_amt_na
            else:
                line.unallocated_amount = 0


class BudgetGopOverhead(models.Model):
    _name = 'budget.gop.overhead'
    _description = "Bugdet overhead Gop"
    _order = 'sequence'

    budget_id = fields.Many2one('project.budget', string='Budget')
    cs_overhead_gop_id = fields.Many2one('material.gop.overhead', 'Overhead GOP ID')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    billed_amt = fields.Float('Billed Amount', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    transferred_amt = fields.Float('Transferred Amount')
    amount_total = fields.Float(string="Budget Amount")
    amt_left = fields.Float(string='Budget Amount Left', compute="_budget_amount_left")
    amt_res = fields.Float(string='Reserved Budget Amount')
    amt_used = fields.Float('Actual Used Amount', default=0.00)
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    dif_amt_used = fields.Float('Actual Used Amount on different budget', default=0.00)
    budget_amount = fields.Float(string="Sheet Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Budget Amount")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='budget_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    # Carry Over
    carried_amt = fields.Float('Carried Amount (receive)', default=0.00)
    carry_amt = fields.Float('Carried Amount (send)', default=0.00)
    status = fields.Selection([('carry', ' Carry Over')],
                              string="Status")
    carried_to = fields.Many2one('project.budget', string='Carried To')
    carried_from = fields.Many2one('project.budget', string='Carried From')
    carried_over = fields.Boolean(string='Carried Over')
    project_id = fields.Many2one(related='budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    amount_return = fields.Float('Return Amount', default=0.00)

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('budget_id.budget_overhead_gop_ids', 'budget_id.budget_overhead_gop_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.budget_id.budget_overhead_gop_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('amount_total', 'amt_res', 'purchased_amt')
    def _budget_amount_left(self):
        for line in self:
            line.amt_left = line.amount_total + line.carried_amt - (
                    line.amt_res + line.purchased_amt + line.carry_amt + line.amount_return + line.transferred_amt)

    def _unused_amt(self):
        for line in self:
            line.unused_amt = line.amount_total - line.amt_used - line.dif_amt_used

    def _get_unallocated(self):
        for line in self:
            if line.cs_overhead_gop_id:
                line.unallocated_amount = line.cs_overhead_gop_id.product_amt_na
            else:
                line.unallocated_amount = 0


class BudgetGopequipment(models.Model):
    _name = 'budget.gop.equipment'
    _description = "Bugdet equipment Gop"
    _order = 'sequence'

    budget_id = fields.Many2one('project.budget', string='Budget')
    cs_equipment_gop_id = fields.Many2one('material.gop.equipment', 'equipment GOP ID')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    billed_amt = fields.Float('Billed Amount', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    transferred_amt = fields.Float('Transferred Amount')
    amount_total = fields.Float(string="Budget Amount")
    amt_left = fields.Float(string='Budget Amount Left', compute="_budget_amount_left")
    amt_res = fields.Float(string='Reserved Budget Amount')
    amt_used = fields.Float('Actual Used Amount', default=0.00)
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    dif_amt_used = fields.Float('Actual Used Amount on different budget', default=0.00)
    budget_amount = fields.Float(string="Sheet Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Budget Amount")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='budget_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    # Carry Over
    carried_amt = fields.Float('Carried Amount (receive)', default=0.00)
    carry_amt = fields.Float('Carried Amount (send)', default=0.00)
    status = fields.Selection([('carry', ' Carry Over')],
                              string="Status")
    carried_to = fields.Many2one('project.budget', string='Carried To')
    carried_from = fields.Many2one('project.budget', string='Carried From')
    carried_over = fields.Boolean(string='Carried Over')
    project_id = fields.Many2one(related='budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    amount_return = fields.Float('Return Amount', default=0.00)

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('budget_id.budget_equipment_gop_ids', 'budget_id.budget_equipment_gop_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.budget_id.budget_equipment_gop_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('amount_total', 'amt_res', 'purchased_amt')
    def _budget_amount_left(self):
        for line in self:
            line.amt_left = line.amount_total + line.carried_amt - (
                    line.amt_res + line.purchased_amt + line.carry_amt + line.amount_return)

    def _unused_amt(self):
        for line in self:
            line.unused_amt = line.amount_total - line.amt_used - line.dif_amt_used

    def _get_unallocated(self):
        for line in self:
            if line.cs_equipment_gop_id:
                line.unallocated_amount = line.cs_equipment_gop_id.product_amt_na
            else:
                line.unallocated_amount = 0


class InternalTransferBudget(models.Model):
    _name = 'bud.internal.transfer.budget.line'
    _description = "Budget Change Request"
    _order = 'sequence'

    project_budget_id = fields.Many2one('project.budget', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    type = fields.Selection([('material', 'Material'),
                             ('labour', 'Labour'),
                             ('overhead', 'Overhead'),
                             ('equipment', 'Equipment'),
                             ('internal_asset', 'Internal Asset'),
                             ('subcon', 'Subcon')],
                            string="Type")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    overhead_category = fields.Selection([
        ('product', 'Product'),
        ('petty cash', 'Petty Cash'),
        ('fuel', 'Fuel'),
        ('cash advance', 'Cash Advance')],
        string="Type")
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    product_id = fields.Many2one('product.product', string='Product')
    variable = fields.Many2one('variable.template', string='Subcon')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    cur_qty = fields.Float('Current quantity', default=0.00)
    adj_qty = fields.Float('Ajusted quantity', default=0.00)
    cur_time = fields.Float('Current time', default=0.00)
    cur_contractors = fields.Float('Current contractors', default=0.00)
    adj_time = fields.Float('Adjusted time', default=0.00)
    adj_contractors = fields.Float('Adjusted contractors', default=0.00)
    cur_unit_price = fields.Float('Current unit price', default=0.00)
    adj_unit_price = fields.Float('Ajusted unit price', default=0.00)
    cur_amt = fields.Float('Current amount', default=0.00)
    adj_amt = fields.Float('Adjusted amount', default=0.00)
    adjusted = fields.Float('Adjusted', default=0.00)
    project_id = fields.Many2one(related='project_budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    is_newly_added_product = fields.Boolean('Is newly added product')
    is_not_from_cost_sheet = fields.Boolean('Is not from cost sheet')


    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('project_budget_id.itb_line_bud_ids', 'project_budget_id.itb_line_bud_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.itb_line_bud_ids:
                no += 1
                l.sr_no = no


class InternalTransferBudgetHistory(models.Model):
    _name = 'bud.internal.transfer.budget.history'
    _description = "Budget Change Request History"
    _order = 'sequence'

    project_budget_id = fields.Many2one('project.budget', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    date = fields.Datetime(string="Change Date")
    itb_id = fields.Many2one('internal.transfer.budget', string='Internal Transfer Budget Id')
    free_amt = fields.Float('Free Amount', default=0.00)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancelled')
    ], string='State')

    @api.depends('project_budget_id.history_itb_bud_ids', 'project_budget_id.history_itb_bud_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.history_itb_bud_ids:
                no += 1
                l.sr_no = no


class BudgetTransferLine(models.Model):
    _name = 'budget.transfer.line'
    _description = "Budget Transfer"
    _order = 'sequence'

    project_budget_id = fields.Many2one('project.budget', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    type = fields.Selection([('material', 'Material'),
                             ('labour', 'Labour'),
                             ('overhead', 'Overhead'),
                             ('equipment', 'Equipment'),
                             ('subcon', 'Subcon')],
                            string="Type")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    variable = fields.Many2one('variable.template', string='Subcon')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    cur_qty = fields.Float('Current quantity', default=0.00)
    adj_qty = fields.Float('Ajusted quantity', default=0.00)
    cur_unit_price = fields.Float('Current unit price', default=0.00)
    adj_unit_price = fields.Float('Ajusted unit price', default=0.00)
    cur_amt = fields.Float('Current amount', default=0.00)
    adj_amt = fields.Float('Adjusted amount', default=0.00)
    adjusted = fields.Float('Allocation', default=0.00)
    project_id = fields.Many2one(related='project_budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('project_budget_id.budget_transfer_line_ids', 'project_budget_id.budget_transfer_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.budget_transfer_line_ids:
                no += 1
                l.sr_no = no


class TransferBudgetHistory(models.Model):
    _name = 'budget.transfer.history'
    _description = "Transfer History"
    _order = 'sequence'

    project_budget_id = fields.Many2one('project.budget', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    date = fields.Datetime(string="Change Date")
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    project_id = fields.Many2one('project.project', string='Project')
    project_budget = fields.Many2one('project.budget', string='From Project Budget')
    dest_project_budget = fields.Many2one('project.budget', string='To Project Budget')
    pbt_id = fields.Many2one('internal.transfer.budget', string='Budget Transfer Id')
    send_amount = fields.Float('Send Amount', default=0.00)
    allocation_amount = fields.Float('Receive Amount', default=0.00)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancelled')
    ], string='State')

    @api.depends('project_budget_id.history_bt_ids', 'project_budget_id.history_bt_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.history_bt_ids:
                no += 1
                l.sr_no = no


class BudgetChangeAllocationLine(models.Model):
    _name = 'budget.change.allocation.line'
    _description = "Budget Change Allocation Line"
    _order = 'sequence'

    project_budget_id = fields.Many2one('project.budget', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    type = fields.Selection([('material', 'Material'),
                             ('labour', 'Labour'),
                             ('overhead', 'Overhead'),
                             ('equipment', 'Equipment'),
                             ('internal_asset', 'Internal Asset'),
                             ('subcon', 'Subcon')],
                            string="Type")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    overhead_category = fields.Selection([
                             ('product', 'Product'),
                             ('petty cash', 'Petty Cash'),
                             ('fuel', 'Fuel'),
                             ('cash advance', 'Cash Advance')],
                            string="Type")
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    product_id = fields.Many2one('product.product', string='Product')
    variable = fields.Many2one('variable.template', string='Subcon')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    cur_qty = fields.Float('Current quantity', default=0.00)
    cur_time = fields.Float('Current time', default=0.00)
    cur_contractors = fields.Float('Current contractors', default=0.00)
    adj_time = fields.Float('Adjusted time', default=0.00)
    adj_contractors = fields.Float('Adjusted contractors', default=0.00)
    adj_qty = fields.Float('Ajusted quantity', default=0.00)
    cur_unit_price = fields.Float('Current unit price', default=0.00)
    adj_unit_price = fields.Float('Ajusted unit price', default=0.00)
    cur_amt = fields.Float('Current amount', default=0.00)
    adj_amt = fields.Float('Adjusted amount', default=0.00)
    adjusted = fields.Float('Adjusted', default=0.00)
    project_id = fields.Many2one(related='project_budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('project_budget_id.budget_change_allocation_line_ids',
                 'project_budget_id.budget_change_allocation_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.budget_change_allocation_line_ids:
                no += 1
                l.sr_no = no


class BudgetChangeAllocationHistory(models.Model):
    _name = 'budget.change.allocation.history'
    _description = "Budget Change Allocation History"
    _order = 'sequence'

    project_budget_id = fields.Many2one('project.budget', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    date = fields.Datetime(string="Change Date")
    itb_id = fields.Many2one('internal.transfer.budget', string='Internal Transfer Budget Id')
    free_amt = fields.Float('Free Amount', default=0.00)
    adjusted_amt = fields.Float('Adjusted Amount', default=0.00)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancelled')
    ], string='State')

    @api.depends('project_budget_id.budget_change_allocation_history_ids',
                 'project_budget_id.budget_change_allocation_history_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.budget_change_allocation_history_ids:
                no += 1
                l.sr_no = no


class BudgetClaimHistory(models.Model):
    _name = 'budget.claim.history'
    _description = "Budget Left Claimed History"
    _order = 'sequence'

    project_budget_id = fields.Many2one('project.budget', string="Cost Sheet", ondelete='cascade')
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    type = fields.Selection([('material', 'Material'),
                             ('labour', 'Labour'),
                             ('overhead', 'Overhead'),
                             ('equipment', 'Equipment'),
                             ('subcon', 'Subcon')],
                            string="Type")
    project_scope_id = fields.Many2one('project.scope.line', string='Project Scope')
    section_id = fields.Many2one('section.line', string='Section')
    variable_id = fields.Many2one('variable.template', string='Variable')
    group_of_product_id = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    subcon_id = fields.Many2one('variable.template', string='Subcon')
    # description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    budget_amount = fields.Float('Budgeted Amount', default=0.00)
    budget_claim_amount = fields.Float('Budget Left Claimed Amount', default=0.00)
    project_id = fields.Many2one(related='project_budget_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')

    @api.depends('project_id.project_section_ids', 'project_scope_id')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope_id:
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope_id.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('project_budget_id')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            if line.type == 'material':
                for l in line.project_budget_id.material_budget_claim_history_ids:
                    no += 1
                    l.sr_no = no
            elif line.type == 'labour':
                for l in line.project_budget_id.labour_budget_claim_history_ids:
                    no += 1
                    l.sr_no = no
            elif line.type == 'overhead':
                for l in line.project_budget_id.overhead_budget_claim_history_ids:
                    no += 1
                    l.sr_no = no
            elif line.type == 'equipment':
                for l in line.project_budget_id.equipment_budget_claim_history_ids:
                    no += 1
                    l.sr_no = no
            elif line.type == 'subcon':
                for l in line.project_budget_id.subcon_budget_claim_history_ids:
                    no += 1
                    l.sr_no = no


class ProjectBudgetApprovalMatrixLine(models.Model):
    _name = 'project.budget.approval.matrix.line'
    _description = 'Approval Matrix Table For Project'

    seq_no = fields.Char('Sequence')
    user_id = fields.Many2many('res.users', string='User')
    min_approver = fields.Integer(string='Minimum Approver')
    # approval_status = fields.Text(string='Approval Status')
    approval_status = fields.Selection([
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval Status')
    time_stamp = fields.Datetime(string='Timestamp')
    feedback = fields.Char(string='Feedback')
    project_budget_id = fields.Many2one('project.budget', string='Budget Project')


class MaterialBudgetCarryOverHistory(models.Model):
    _name = 'material.budget.carry.over.history'
    _description = "Material Budget Claim Over History"

    project_budget_id = fields.Many2one('project.budget', string="Project Budget")
    bd_material_id = fields.Many2one('budget.material', string='Material')
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    date = fields.Datetime(string="Date")
    project_scope_id = fields.Many2one('project.scope.line', string='Project Scope')
    section_id = fields.Many2one('section.line', string='Section')
    group_of_product_id = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    carry_send_qty = fields.Float('Carried Quantity(Sent)', default=0.00)
    carry_send_amt = fields.Float('Carried Amount(Sent)', default=0.00)
    carry_from_qty = fields.Float('Carried Quantity(Receive)', default=0.00)
    carry_from_amt = fields.Float('Carried Amount(Receive)', default=0.00)
    unit_price = fields.Float('Unit Price', default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    carried_to_id = fields.Many2one('project.budget', string='Carried To')
    carried_from_id = fields.Many2one('project.budget', string='Carried From')

    @api.depends('project_budget_id.material_budget_carry_over_history_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.material_budget_carry_over_history_ids:
                no += 1
                l.sr_no = no


class LabourBudgetCarryOverHistory(models.Model):
    _name = 'labour.budget.carry.over.history'
    _description = "Labour Budget Carry Over History"

    project_budget_id = fields.Many2one('project.budget', string="Project Budget")
    bd_labour_id = fields.Many2one('budget.labour', string='Labour')
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    date = fields.Datetime(string="Date")
    project_scope_id = fields.Many2one('project.scope.line', string='Project Scope')
    section_id = fields.Many2one('section.line', string='Section')
    group_of_product_id = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    carry_send_amt = fields.Float('Carried Amount(Sent)', default=0.00)
    carry_send_contractors = fields.Float('Carried Contractors(Sent)', default=0.00)
    carry_send_time = fields.Float('Carried Time(Sent)', default=0.00)
    carry_from_amt = fields.Float('Carried Amount(Receive)', default=0.00)
    carry_from_contractors = fields.Float('Carried Contractors(Receive)', default=0.00)
    carry_from_time = fields.Float('Carried Time(Receive)', default=0.00)
    unit_price = fields.Float('Unit Price', default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    carried_to_id = fields.Many2one('project.budget', string='Carried To')
    carried_from_id = fields.Many2one('project.budget', string='Carried From')

    @api.depends('project_budget_id.labour_budget_carry_over_history_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.labour_budget_carry_over_history_ids:
                no += 1
                l.sr_no = no


class OverheadBudgetCarryOverHistory(models.Model):
    _name = 'overhead.budget.carry.over.history'
    _description = "Overhead Budget Claim Over History"

    project_budget_id = fields.Many2one('project.budget', string="Project Budget")
    bd_overhead_id = fields.Many2one('budget.overhead', string='Overhead')
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    date = fields.Datetime(string="Date")
    project_scope_id = fields.Many2one('project.scope.line', string='Project Scope')
    section_id = fields.Many2one('section.line', string='Section')
    group_of_product_id = fields.Many2one('group.of.product', string='Group of Product')
    overhead_category = fields.Selection(
        [('product', 'Product'), ('petty cash', 'Petty Cash'), ('cash advance', 'Cash Advance'), ('fuel', 'Fuel')],
        required=True)
    product_id = fields.Many2one('product.product', string='Product')
    carry_send_qty = fields.Float('Carried Quantity(Sent)', default=0.00)
    carry_send_amt = fields.Float('Carried Amount(Sent)', default=0.00)
    carry_from_qty = fields.Float('Carried Quantity(Receive)', default=0.00)
    carry_from_amt = fields.Float('Carried Amount(Receive)', default=0.00)
    unit_price = fields.Float('Unit Price', default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    carried_to_id = fields.Many2one('project.budget', string='Carried To')
    carried_from_id = fields.Many2one('project.budget', string='Carried From')

    @api.depends('project_budget_id.overhead_budget_carry_over_history_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.overhead_budget_carry_over_history_ids:
                no += 1
                l.sr_no = no


class EquipmentBudgetCarryOverHistory(models.Model):
    _name = 'equipment.budget.carry.over.history'
    _description = "Equipment Budget Carry Over History"

    project_budget_id = fields.Many2one('project.budget', string="Project Budget")
    bd_equipment_id = fields.Many2one('budget.equipment', string='Equipment')
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    date = fields.Datetime(string="Date")
    project_scope_id = fields.Many2one('project.scope.line', string='Project Scope')
    section_id = fields.Many2one('section.line', string='Section')
    group_of_product_id = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    carry_send_qty = fields.Float('Carried Quantity(Sent)', default=0.00)
    carry_send_amt = fields.Float('Carried Amount(Sent)', default=0.00)
    carry_from_qty = fields.Float('Carried Quantity(Receive)', default=0.00)
    carry_from_amt = fields.Float('Carried Amount(Receive)', default=0.00)
    unit_price = fields.Float('Unit Price', default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    carried_to_id = fields.Many2one('project.budget', string='Carried To')
    carried_from_id = fields.Many2one('project.budget', string='Carried From')

    @api.depends('project_budget_id.equipment_budget_carry_over_history_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.equipment_budget_carry_over_history_ids:
                no += 1
                l.sr_no = no


class InternalAssetBudgetCarryOverHistory(models.Model):
    _name = 'internal.asset.budget.carry.over.history'
    _description = "Internal Asset Budget Claim Over History"

    project_budget_id = fields.Many2one('project.budget', string="Project Budget")
    bd_internal_asset_id = fields.Many2one('budget.internal.asset', string='Internal Asset')
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    date = fields.Datetime(string="Date")
    project_scope_id = fields.Many2one('project.scope.line', string='Project Scope')
    section_id = fields.Many2one('section.line', string='Section')
    asset_category_id = fields.Many2one('maintenance.equipment.category', string="Asset Category", required=True)
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    carry_send_qty = fields.Float('Carried Quantity(Sent)', default=0.00)
    carry_send_amt = fields.Float('Carried Amount(Sent)', default=0.00)
    carry_from_qty = fields.Float('Carried Quantity(Receive)', default=0.00)
    carry_from_amt = fields.Float('Carried Amount(Receive)', default=0.00)
    unit_price = fields.Float('Unit Price', default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    carried_to_id = fields.Many2one('project.budget', string='Carried To')
    carried_from_id = fields.Many2one('project.budget', string='Carried From')

    @api.depends('project_budget_id.internal_asset_budget_carry_over_history_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.internal_asset_budget_carry_over_history_ids:
                no += 1
                l.sr_no = no


class SubconBudgetCarryOverHistory(models.Model):
    _name = 'subcon.budget.carry.over.history'
    _description = "Subcon Budget Claim Over History"

    project_budget_id = fields.Many2one('project.budget', string="Project Budget")
    bd_subcon_id = fields.Many2one('budget.subcon', string='Subcon')
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    date = fields.Datetime(string="Date")
    project_scope_id = fields.Many2one('project.scope.line', string='Project Scope')
    section_id = fields.Many2one('section.line', string='Section')
    subcon_id = fields.Many2one('variable.template', string='Subcon')
    carry_send_qty = fields.Float('Carried Quantity(Sent)', default=0.00)
    carry_send_amt = fields.Float('Carried Amount(Sent)', default=0.00)
    carry_from_qty = fields.Float('Carried Quantity(Receive)', default=0.00)
    carry_from_amt = fields.Float('Carried Amount(Receive)', default=0.00)
    unit_price = fields.Float('Unit Price', default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    carried_to_id = fields.Many2one('project.budget', string='Carried To')
    carried_from_id = fields.Many2one('project.budget', string='Carried From')

    @api.depends('project_budget_id.subcon_budget_carry_over_history_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_budget_id.subcon_budget_carry_over_history_ids:
                no += 1
                l.sr_no = no
