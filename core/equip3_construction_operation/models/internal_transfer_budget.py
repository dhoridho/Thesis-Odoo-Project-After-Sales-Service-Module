from odoo import _, api, fields, models
from datetime import datetime, date
from odoo.exceptions import ValidationError, UserError
from pytz import timezone
from lxml import etree


class BudgetChangeRequest(models.Model):
    _name = 'internal.transfer.budget'
    _description = 'Budget Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Name', copy=False, readonly=True, states={'draft': [('readonly', True)]}, index=True,
                       default=lambda self: _('New'))
    active = fields.Boolean(string='Active', default=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('to_approve', 'Waiting for Approval'), ('approved', 'Approved'), ('done', 'Done'),
         ('reject', 'Rejected'), ('cancel', 'Cancelled')], string="State", readonly=True, tracking=True,
        default='draft')
    state1 = fields.Selection(related='state', tracking=False)
    state2 = fields.Selection(related='state', tracking=False)
    state3 = fields.Selection(related='state', tracking=False)
    project_id = fields.Many2one('project.project', string='Project')
    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
    dest_project_id = fields.Many2one('project.project', string='Allocation Project')
    dest_job_sheet_id = fields.Many2one('job.cost.sheet', string="Allocation Cost Sheet", ondelete='cascade')
    project_budget = fields.Many2one('project.budget', string='Periodical Budget')
    dest_project_budget = fields.Many2one('project.budget', string='Allocation Periodical Budget')
    approve_date = fields.Datetime(string='Approved Date', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company.id)
    branch_id = fields.Many2one(related='project_id.branch_id', string="Branch",
                                default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids),
                                                     ('company_id', '=', self.env.company.id)])
    company_currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    create_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.uid, readonly=True)
    free_amt = fields.Float('Available Budget Amount', default=0.00, compute="_compute_free_amt")
    change_amt = fields.Float('Change Amount', default=0.00, Store=True)
    send_amt = fields.Float('Allocation Amount', default=0.00, Store=True)
    itb_change_line_ids = fields.One2many('internal.transfer.budget.change.line', 'itb_id', string='Change Line')
    itb_material_line_ids = fields.One2many('internal.transfer.budget.material.line', 'itb_id',
                                            domain="[('is_delete', '=', False)]", string='Material')
    itb_labour_line_ids = fields.One2many('internal.transfer.budget.labour.line', 'itb_id',
                                          domain="[('is_delete', '=', False)]", string='Labour')
    itb_overhead_line_ids = fields.One2many('internal.transfer.budget.overhead.line', 'itb_id',
                                            domain="[('is_delete', '=', False)]", string='Overhead')
    itb_internal_asset_line_ids = fields.One2many('internal.transfer.budget.internal.asset.line', 'itb_id',
                                                  domain="[('is_delete', '=', False)]", string='Equipment')
    itb_equipment_line_ids = fields.One2many('internal.transfer.budget.equipment.line', 'itb_id',
                                             domain="[('is_delete', '=', False)]", string='Equipment')
    itb_subcon_line_ids = fields.One2many('internal.transfer.budget.subcon.line', 'itb_id',
                                          domain="[('is_delete', '=', False)]", string='Subcon')
    itb_project_scope_ids  = fields.One2many("internal.transfer.budget.project.scope", "itb_id", string="Project Scope")
    itb_section_ids = fields.One2many("internal.transfer.budget.section", "itb_id", string="Section")
    is_project_budget = fields.Boolean("Is Project Budget", default=False)
    is_budget_transfer = fields.Boolean("Is Budget Transfer", default=False)
    is_project_transfer = fields.Boolean("Is Project Budget Transfer", default=False)
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')
    budgeting_method = fields.Selection(string='Budgeting Method', related='project_id.budgeting_method')
    budgeting_period = fields.Selection(string='Budgeting Period', related='project_id.budgeting_period')

    # approval matrix
    approval_matrix_id = fields.Many2one('approval.matrix.internal.transfer.budget', string="Approval Matrix",
                                         store=True)
    approval_matrix_itb_line_ids = fields.One2many('approval.matrix.internal.transfer.budget.line',
                                                   'internal_transfer_budget_id', store=True,
                                                   string="Approved Matrix")
    is_change_request_approval_matrix = fields.Boolean(string="Budget Change Request Matrix",
                                                       compute='is_budget_req_approval_matrix', store=False, )
    is_project_transfer_approval_matrix = fields.Boolean(string="Project Transfer Approval Matrix",
                                                         compute='is_proj_transfer_approval_matrix', store=False)
    is_asset_allocation_approval_matrix = fields.Boolean(string="Change Allocation Approval Matrix",
                                                         compute='_is_asset_allocation_approval_matrix', store=False)
    is_approval_matrix_filled = fields.Boolean(string="Custome Matrix", store=False)
    user_is_approver = fields.Boolean(string='Is Approve Button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.internal.transfer.budget.line',
                                              string='Internal Budget Approval Matrix Line',
                                              store=False)

    approving_matrix_budget_change_id = fields.Many2one('approval.matrix.internal.transfer.budget',
                                                        string="Approval Matrix",
                                                        compute='_compute_approving_customer_matrix', store=True)
    budget_change_user_ids = fields.One2many('budget.change.approver.user', 'budget_change_approver_id',
                                             string='Approver')
    approvers_ids = fields.Many2many('res.users', 'budget_change_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    employee_id = fields.Many2one('res.users', string='Users')
    last_approved = fields.Many2one('res.users', string='Users')
    is_change_allocation = fields.Boolean(string='Is Change Allocation', default=False)
    is_continue_over_budget = fields.Boolean(string="Is Continue Over Budget")

    @api.onchange('project_id', 'is_project_transfer', 'is_change_allocation')
    def _onchange_project_budget_domain(self):
        for rec in self:
            if rec.is_project_transfer == False and rec.is_change_allocation == False:
                return {
                    'domain': {
                        'project_budget': [('project_id', '=', rec.project_id.id)]}
                }
            elif rec.is_project_transfer == False and rec.is_change_allocation == True:
                return {
                    'domain': {
                        'project_budget': [('project_id', '=', rec.project_id.id), ('state', '=', 'in_progress')]}
                }
            elif rec.is_project_transfer == True and rec.is_change_allocation == False:
                return {
                    'domain': {
                        'project_budget': [('project_id', '=', rec.project_id.id), ('state', '=', 'in_progress')]}
                }

    @api.onchange('project_budget')
    def _onchange_project_budget_validation(self):
        for rec in self:
            if rec.project_budget:
                if rec.project_budget.state == 'draft' and rec.project_budget.is_must_refresh == True:
                    raise ValidationError(
                        _("Please refresh line the periodical budget selected first to set budget up to date."))

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))

        return super(BudgetChangeRequest, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))

        return super(BudgetChangeRequest, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                           orderby=orderby, lazy=lazy)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(BudgetChangeRequest, self).fields_view_get(
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

    @api.depends('project_id')
    def is_budget_req_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_change_request_approval_matrix = IrConfigParam.get_param('budget_change_request_approval_matrix')
        for record in self:
            record.is_change_request_approval_matrix = is_change_request_approval_matrix

    @api.depends('project_id')
    def is_proj_transfer_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_project_transfer_approval_matrix = IrConfigParam.get_param('project_budget_transfer_approval_matrix')
        for record in self:
            record.is_project_transfer_approval_matrix = is_project_transfer_approval_matrix

    @api.depends('project_id')
    def _is_asset_allocation_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_asset_allocation_approval_matrix = IrConfigParam.get_param('is_asset_allocation_approval_matrix')
        for record in self:
            record.is_asset_allocation_approval_matrix = is_asset_allocation_approval_matrix

    @api.depends('is_project_transfer_approval_matrix', 'is_change_request_approval_matrix', 'project_id',
                 'branch_id', 'company_id', 'department_type', 'send_amt', 'is_project_transfer', 'free_amt')
    def _compute_approving_customer_matrix(self):
        # ------ for approval matrix table --------
        for res in self:
            res.approving_matrix_budget_change_id = False

            if res.is_change_request_approval_matrix:
                if res.is_project_transfer == False and res.is_change_allocation == False:
                    if res.department_type == 'project':
                        approving_matrix_budget_change_id = self.env['approval.matrix.internal.transfer.budget'].search(
                            [
                                ('company_id', '=', res.company_id.id),
                                ('branch_id', '=', res.branch_id.id),
                                ('project', 'in', (res.project_id.id)),
                                ('department_type', '=', 'project'),
                                ('set_default', '=', False),
                                ('is_project_transfer', '=', False),
                                ('is_change_allocation', '=', False),
                                ('minimum_amt', '<=', res.free_amt),
                                ('maximum_amt', '>=', res.free_amt)
                                ], limit=1)

                        approving_matrix_default = self.env['approval.matrix.internal.transfer.budget'].search([
                            ('company_id', '=', res.company_id.id),
                            ('branch_id', '=', res.branch_id.id),
                            ('set_default', '=', True),
                            ('department_type', '=', 'project'),
                            ('is_project_transfer', '=', False),
                            ('is_change_allocation', '=', False),
                            ('minimum_amt', '<=', res.free_amt),
                            ('maximum_amt', '>=', res.free_amt)], limit=1)

                    else:
                        approving_matrix_budget_change_id = self.env['approval.matrix.internal.transfer.budget'].search(
                            [
                                ('company_id', '=', res.company_id.id),
                                ('branch_id', '=', res.branch_id.id),
                                ('project', 'in', (res.project_id.id)),
                                ('department_type', '=', 'department'),
                                ('set_default', '=', False),
                                ('is_project_transfer', '=', False),
                                ('is_change_allocation', '=', False),
                                ('minimum_amt', '<=', res.free_amt),
                                ('maximum_amt', '>=', res.free_amt)], limit=1)

                        approving_matrix_default = self.env['approval.matrix.internal.transfer.budget'].search([
                            ('company_id', '=', res.company_id.id),
                            ('branch_id', '=', res.branch_id.id),
                            ('set_default', '=', True),
                            ('department_type', '=', 'department'),
                            ('is_project_transfer', '=', False),
                            ('is_change_allocation', '=', False),
                            ('minimum_amt', '<=', res.free_amt),
                            ('maximum_amt', '>=', res.free_amt)], limit=1)


                    if approving_matrix_budget_change_id:
                        res.approving_matrix_budget_change_id = approving_matrix_budget_change_id and approving_matrix_budget_change_id.id or False
                    else:
                        if approving_matrix_default:
                            res.approving_matrix_budget_change_id = approving_matrix_default and approving_matrix_default.id or False

            if res.is_asset_allocation_approval_matrix:
                if res.is_project_transfer == False and res.is_change_allocation == True:
                    if res.department_type == 'project':
                        approving_matrix_budget_change_id = self.env['approval.matrix.internal.transfer.budget'].search(
                            [
                                ('company_id', '=', res.company_id.id),
                                ('branch_id', '=', res.branch_id.id),
                                ('project', 'in', (res.project_id.id)),
                                ('department_type', '=', 'project'),
                                ('set_default', '=', False),
                                ('is_project_transfer', '=', False),
                                ('is_change_allocation', '=', True)], limit=1)

                        approving_matrix_default = self.env['approval.matrix.internal.transfer.budget'].search([
                            ('company_id', '=', res.company_id.id),
                            ('branch_id', '=', res.branch_id.id),
                            ('set_default', '=', True),
                            ('department_type', '=', 'project'),
                            ('is_project_transfer', '=', False),
                            ('is_change_allocation', '=', True)], limit=1)

                    else:
                        approving_matrix_budget_change_id = self.env['approval.matrix.internal.transfer.budget'].search(
                            [
                                ('company_id', '=', res.company_id.id),
                                ('branch_id', '=', res.branch_id.id),
                                ('project', 'in', (res.project_id.id)),
                                ('department_type', '=', 'department'),
                                ('set_default', '=', False),
                                ('is_project_transfer', '=', False),
                                ('is_change_allocation', '=', True)], limit=1)

                        approving_matrix_default = self.env['approval.matrix.internal.transfer.budget'].search([
                            ('company_id', '=', res.company_id.id),
                            ('branch_id', '=', res.branch_id.id),
                            ('set_default', '=', True),
                            ('department_type', '=', 'department'),
                            ('is_project_transfer', '=', False),
                            ('is_change_allocation', '=', True)], limit=1)

                    if approving_matrix_budget_change_id:
                        res.approving_matrix_budget_change_id = approving_matrix_budget_change_id and approving_matrix_budget_change_id.id or False
                    else:
                        if approving_matrix_default:
                            res.approving_matrix_budget_change_id = approving_matrix_default and approving_matrix_default.id or False

            if res.is_project_transfer_approval_matrix:
                if res.is_project_transfer == True and res.is_change_allocation == False:
                    if res.department_type == 'project':
                        approving_matrix_budget_change_id = self.env['approval.matrix.internal.transfer.budget'].search(
                            [
                                ('company_id', '=', res.company_id.id),
                                ('branch_id', '=', res.branch_id.id),
                                ('project', 'in', (res.project_id.id)),
                                ('department_type', '=', 'project'),
                                ('set_default', '=', False),
                                ('is_project_transfer', '=', True),
                                ('is_change_allocation', '=', False),
                                ('minimum_amt', '<=', res.send_amt),
                                ('maximum_amt', '>=', res.send_amt), ], limit=1)

                        approving_matrix_default = self.env['approval.matrix.internal.transfer.budget'].search([
                            ('company_id', '=', res.company_id.id),
                            ('branch_id', '=', res.branch_id.id),
                            ('set_default', '=', True),
                            ('department_type', '=', 'project'),
                            ('is_project_transfer', '=', True),
                            ('is_change_allocation', '=', False),
                            ('minimum_amt', '<=', res.send_amt),
                            ('maximum_amt', '>=', res.send_amt)], limit=1)

                    else:
                        approving_matrix_budget_change_id = self.env['approval.matrix.internal.transfer.budget'].search(
                            [
                                ('company_id', '=', res.company_id.id),
                                ('branch_id', '=', res.branch_id.id),
                                ('project', 'in', (res.project_id.id)),
                                ('department_type', '=', 'department'),
                                ('set_default', '=', False),
                                ('is_project_transfer', '=', True),
                                ('is_change_allocation', '=', False),
                                ('minimum_amt', '<=', res.send_amt),
                                ('maximum_amt', '>=', res.send_amt)], limit=1)

                        approving_matrix_default = self.env['approval.matrix.internal.transfer.budget'].search([
                            ('company_id', '=', res.company_id.id),
                            ('branch_id', '=', res.branch_id.id),
                            ('set_default', '=', True),
                            ('department_type', '=', 'department'),
                            ('is_project_transfer', '=', True),
                            ('is_change_allocation', '=', False),
                            ('minimum_amt', '<=', res.send_amt),
                            ('maximum_amt', '>=', res.send_amt)], limit=1)

                    if approving_matrix_budget_change_id:
                        res.approving_matrix_budget_change_id = approving_matrix_budget_change_id and approving_matrix_budget_change_id.id or False
                    else:
                        if approving_matrix_default:
                            res.approving_matrix_budget_change_id = approving_matrix_default and approving_matrix_default.id or False

    @api.onchange('project_id', 'approving_matrix_budget_change_id')
    def onchange_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.project_id:
                app_list = []
                if record.is_change_request_approval_matrix or record.is_project_transfer_approval_matrix:
                    record.budget_change_user_ids = []
                    for rec in record.approving_matrix_budget_change_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'user_ids': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                    record.approvers_ids = app_list
                    record.budget_change_user_ids = data

    def _compute_is_approver(self):
        for record in self:
            if record.approvers_ids:
                current_user = record.env.user
                matrix_line = sorted(record.budget_change_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(record.budget_change_user_ids)
                if app < a:
                    for line in record.budget_change_user_ids[app]:
                        if current_user in line.user_ids:
                            record.is_approver = True
                        else:
                            record.is_approver = False
                else:
                    record.is_approver = False
            else:
                record.is_approver = False

    def check_quantity(self):
        is_over = False
        for rec in self:
            for material in rec.itb_material_line_ids:
                if material.adj_qty > material.unallocated_qty:
                    is_over = True
                    break
                elif material.adj_qty + material.cur_qty < 0:
                    is_over = True
                    break
            for labour in rec.itb_labour_line_ids:
                if labour.adj_time > labour.unallocated_time:
                    is_over = True
                    break
                elif labour.adj_time + labour.cur_time < 0:
                    is_over = True
                    break
                if labour.adj_contractors > labour.unallocated_contractors:
                    is_over = True
                    break
                elif labour.adj_contractors + labour.cur_contractors < 0:
                    is_over = True
                    break
            for overhead in rec.itb_overhead_line_ids:
                if overhead.adj_qty > overhead.unallocated_qty:
                    is_over = True
                    break
                elif overhead.adj_qty + overhead.cur_qty < 0:
                    is_over = True
                    break
            for asset in rec.itb_internal_asset_line_ids:
                if asset.adj_qty > asset.unallocated_qty:
                    is_over = True
                    break
                elif asset.adj_qty + asset.cur_qty < 0:
                    is_over = True
                    break
            for equipment in rec.itb_equipment_line_ids:
                if equipment.adj_qty > equipment.unallocated_qty:
                    is_over = True
                    break
                elif equipment.adj_qty + equipment.cur_qty < 0:
                    is_over = True
                    break
            for subcon in rec.itb_subcon_line_ids:
                if subcon.adj_qty > subcon.unallocated_qty:
                    is_over = True
                    break
                elif subcon.adj_qty + subcon.cur_qty < 0:
                    is_over = True
                    break
        return is_over

    def request_approval(self):
        for record in self:
            # Budget Change Request
            if record.is_project_transfer is False and record.is_change_allocation is False:
                if record.free_amt < 0 and not record.is_continue_over_budget:
                    return {
                        'name': "Warning",
                        'view_mode': 'form',
                        'res_model': 'internal.transfer.budget.over.budget.validation',
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': {
                            'default_is_approval_matrix': True,
                            'default_warning_message': "Cost Sheet Budget will over the Contract Budget, "
                                               "are you sure want to continue?",
                            'default_itb_id': record.id
                        }
                    }
                    # raise ValidationError(_("The available budget amount cannot below 0."))

                if not record.itb_change_line_ids:
                    raise ValidationError(_("You don't make any changes. Please make changes first"))

                if len(self.budget_change_user_ids) == 0:
                    raise ValidationError(
                        _("There's no budget change approval matrix for this project or approval matrix default created. You have to create it first."))

                if not record.itb_change_line_ids:
                    raise ValidationError(_("You don't make any changes. Please make changes first"))

                action_id = self.env.ref('equip3_construction_operation.budget_change_request_menu_action')
                template_id = self.env.ref('equip3_construction_operation.email_template_reminder_for_budget_change')

            # Change Allocation Request
            elif record.is_project_transfer is False and record.is_change_allocation is True:
                if len(self.budget_change_user_ids) == 0:
                    raise ValidationError(
                        _("There's no change allocation change approval matrix for this project or approval matrix default created. You have to create it first."))

                if not record.itb_change_line_ids:
                    raise ValidationError(_("You don't make any changes. Please make changes first"))

                if record.check_quantity():
                    raise ValidationError(_("The adjusted quantity cannot greater than the unallocated quantity "
                                            "or less than current quantity"))

                action_id = self.env.ref('equip3_construction_operation.project_change_allocation_menu_action')
                template_id = self.env.ref(
                    'equip3_construction_operation.email_template_reminder_for_change_allocation')

            # Project Budget Transfer
            elif record.is_project_transfer is True and record.is_change_allocation is False:
                if len(self.budget_change_user_ids) == 0:
                    raise ValidationError(
                        _("There's no project budget transfer approval matrix for this project or approval matrix default created. You have to create it first."))

                if record.send_amt <= 0:
                    raise ValidationError(_("The allocation amount cannot less than or equal to 0."))

                amount = record.free_amt - record.send_amt
                if amount < 0:
                    raise ValidationError(_("The allocation amount cannot greater than the available budget amount"))

                action_id = self.env.ref('equip3_construction_operation.project_budget_transfer_menu_action')
                template_id = self.env.ref(
                    'equip3_construction_operation.email_template_reminder_for_project_budget_transfer')

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=internal.transfer.budget'
            if record.budget_change_user_ids and len(record.budget_change_user_ids[0].user_ids) > 1:
                for approved_matrix_id in record.budget_change_user_ids[0].user_ids:
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
                approver = record.budget_change_user_ids[0].user_ids[0]
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

            for line in record.budget_change_user_ids:
                line.write({'approver_state': 'draft'})

    def approve(self):
        sequence_matrix = [data.name for data in self.budget_change_user_ids]
        sequence_approval = [data.name for data in self.budget_change_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.budget_change_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)

        for rec in self:
            # Budget Change Request
            if not rec.is_project_transfer and not rec.is_change_allocation:
                # if rec.free_amt < 0:
                #     raise ValidationError(_("The available budget amount cannot below 0."))

                if not rec.itb_change_line_ids:
                    raise ValidationError(_("You don't make any changes. Please make changes first"))

                action_id = self.env.ref('equip3_construction_operation.budget_change_request_menu_action')
                template_app = self.env.ref('equip3_construction_operation.email_template_budget_change_approved')
                template_id = self.env.ref(
                    'equip3_construction_operation.email_template_reminder_for_budget_change_temp')

            # Change Allocation Request
            elif not rec.is_project_transfer and rec.is_change_allocation:
                if rec.check_quantity():
                    raise ValidationError(_("The adjusted quantity cannot greater than the unallocated quantity "
                                            "or less than current quantity"))

                if not rec.itb_change_line_ids:
                    raise ValidationError(_("You don't make any changes. Please make changes first"))

                action_id = self.env.ref('equip3_construction_operation.project_change_allocation_menu_action')
                template_app = self.env.ref('equip3_construction_operation.email_template_change_allocation_approved')
                template_id = self.env.ref(
                    'equip3_construction_operation.email_template_reminder_for_change_allocation_temp')

            # Project Budget Transfer
            elif rec.is_project_transfer and not rec.is_change_allocation:
                amount = rec.free_amt - rec.send_amt
                if amount < 0:
                    raise ValidationError(_("The allocation amount cannot greater than the available budget amount"))

                amount = rec.free_amt - rec.send_amt
                if amount < 0:
                    raise ValidationError(_("The allocation amount cannot greater than the available budget amount"))

                action_id = self.env.ref('equip3_construction_operation.project_budget_transfer_menu_action')
                template_app = self.env.ref(
                    'equip3_construction_operation.email_template_project_budget_transfer_approved')
                template_id = self.env.ref(
                    'equip3_construction_operation.email_template_reminder_for_project_budget_transfer_temp')

            else:
                if rec.free_amt < 0:
                    raise ValidationError(_("The available budget amount cannot below 0."))

            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(rec.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=internal.transfer.budget'

            current_user = self.env.uid
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"

            if self.env.user not in rec.approved_user_ids:
                if rec.is_approver:
                    for line in rec.budget_change_user_ids:
                        for user in line.user_ids:
                            if current_user == user.user_ids.id:
                                line.timestamp = fields.Datetime.now()
                                rec.approved_user_ids = [(4, current_user)]
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

                    matrix_line = sorted(rec.budget_change_user_ids.filtered(lambda r: r.is_approve == False))
                    if len(matrix_line) == 0:
                        rec.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                        ctx = {
                            'email_from': self.env.user.company_id.email,
                            'email_to': rec.employee_id.email,
                            'date': date.today(),
                            'url': url,
                        }
                        template_app.sudo().with_context(ctx).send_mail(rec.id, True)
                        rec.confirm()

                    else:
                        rec.last_approved = self.env.user.id
                        rec.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                        for approving_matrix_line_user in matrix_line[0].user_ids:
                            ctx = {
                                'email_from': self.env.user.company_id.email,
                                'email_to': approving_matrix_line_user.partner_id.email,
                                'approver_name': approving_matrix_line_user.name,
                                'date': date.today(),
                                'submitter': rec.last_approved.name,
                                'url': url,
                            }
                            template_id.sudo().with_context(ctx).send_mail(rec.id, True)

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
            if not record.is_project_transfer and not record.is_change_allocation:
                action_id = self.env.ref('equip3_construction_operation.budget_change_request_menu_action')
                template_rej = self.env.ref('equip3_construction_operation.email_template_budget_change_rejected')

            elif not record.is_project_transfer and record.is_change_allocation:
                action_id = self.env.ref('equip3_construction_operation.project_change_allocation_menu_action')
                template_rej = self.env.ref('equip3_construction_operation.email_template_change_allocation_rejected')

            elif record.is_project_transfer and not record.is_change_allocation:
                action_id = self.env.ref('equip3_construction_operation.project_budget_transfer_menu_action')
                template_rej = self.env.ref(
                    'equip3_construction_operation.email_template_project_budget_transfer_rejected')

            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=internal.transfer.budget'
            for user in record.budget_change_user_ids:
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
            record.write({'state': 'reject'})

    def reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'approval.matrix.internal.budget.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def cancel_record(self):
        self.write({'state': 'cancel'})

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
                        'domain': {
                            'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'),
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
                        'domain': {
                            'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'),
                                           ('company_id', '=', rec.company_id.id)]}
                    }

    @api.constrains('is_project_transfer')
    def contract_category_cahnge(self):
        if self.is_project_transfer == True:
            self.name = self.env['ir.sequence'].next_by_code('project.budget.transfer.sequence')
        elif self.is_project_transfer == False and self.is_change_allocation == True:
            self.name = self.env['ir.sequence'].next_by_code('change.allocation.sequence')
        else:
            self.name = self.env['ir.sequence'].next_by_code('budget.change.request.sequence')

    @api.onchange('project_id')
    def onchange_project(self):
        self.itb_change_line_ids = [(5, 0, 0)]
        self.itb_material_line_ids = [(5, 0, 0)]
        self.itb_labour_line_ids = [(5, 0, 0)]
        self.itb_overhead_line_ids = [(5, 0, 0)]
        self.itb_internal_asset_line_ids = [(5, 0, 0)]
        self.itb_equipment_line_ids = [(5, 0, 0)]
        self.itb_subcon_line_ids = [(5, 0, 0)]
        for rec in self:
            if self.project_id:
                cost = rec.env['job.cost.sheet'].search(
                    [('project_id', '=', rec.project_id.id), ('state', '=', 'in_progress')])
                if not cost:
                    raise ValidationError(_("Please nn progress the cost sheet for this project first."))
                else:
                    rec.write({'job_sheet_id': cost})
                if self.is_change_allocation:
                    if self.project_id.budgeting_period == 'project':
                        raise ValidationError(_("Project budgeting period must be 'Monthly' or 'Custom'"))

    @api.onchange('dest_project_id')
    def onchange_dest_project(self):
        for rec in self:
            if rec.dest_project_id:
                if rec.dest_project_id == rec.project_id:
                    raise ValidationError(_("Allocation project cannot be the same as the project"))
                cost = rec.env['job.cost.sheet'].search([('project_id', '=', rec.dest_project_id.id),
                                                         ('state', 'not in', ['cancelled', 'reject', 'revised'])])
                rec.write({'dest_job_sheet_id': cost})
                if not cost:
                    raise ValidationError(_("Please select project that have cost sheet"))
                elif rec.dest_project_id.primary_states != 'progress':
                    raise ValidationError(_("Project must be in 'In Progress' state"))

    @api.onchange('dest_project_budget')
    def onchange_dest_project_budget(self):
        for rec in self:
            if rec.dest_project_budget:
                if rec.dest_project_budget == rec.project_budget:
                    raise ValidationError(_("Allocation project budget cannot be the same as the project budget"))
                elif rec.dest_project_budget.state != 'in_progress':
                    raise ValidationError(_("Project budget must be in 'In Progress' state"))

    def get_material(self, mat):
        return {
            'project_scope': mat.project_scope.id,
            'section_name': mat.section_name.id,
            'variable_ref': mat.variable_ref.id,
            'product_id': mat.product_id.id,
            'description': mat.description,
            'group_of_product': mat.group_of_product.id,
            'cur_qty': mat.budgeted_qty_left,
            'cur_unit_price': mat.price_unit,
            'adj_unit_price': mat.price_unit,
            'uom_id': mat.uom_id.id,
            'cur_amt': mat.budgeted_amt_left,
            'is_generated': True
        }

    def get_labour(self, lab):
        return {
            'project_scope': lab.project_scope.id,
            'section_name': lab.section_name.id,
            'variable_ref': lab.variable_ref.id,
            'product_id': lab.product_id.id,
            'description': lab.description,
            'group_of_product': lab.group_of_product.id,
            'cur_qty': lab.budgeted_qty_left,
            'cur_unit_price': lab.price_unit,
            'adj_unit_price': lab.price_unit,
            'uom_id': lab.uom_id.id,
            'cur_amt': lab.budgeted_amt_left,
            'is_generated': True
        }

    def get_overhead(self, ove):
        return {
            'project_scope': ove.project_scope.id,
            'section_name': ove.section_name.id,
            'variable_ref': ove.variable_ref.id,
            'product_id': ove.product_id.id,
            'description': ove.description,
            'overhead_catagory': ove.overhead_catagory,
            'group_of_product': ove.group_of_product.id,
            'cur_qty': ove.budgeted_qty_left,
            'cur_unit_price': ove.price_unit,
            'adj_unit_price': ove.price_unit,
            'uom_id': ove.uom_id.id,
            'cur_amt': ove.budgeted_amt_left,
            'is_generated': True
        }

    def get_internal_asset(self, asset):
        return {
            'project_scope': asset.project_scope.id,
            'section_name': asset.section_name.id,
            'asset_category_id': asset.asset_category_id.id,
            'asset_id': asset.asset_id.id,
            'description': asset.description,
            'cur_qty': asset.budgeted_qty_left,
            'cur_amt': asset.budgeted_amt_left,
            'cur_unit_price': asset.price_unit,
            'adj_unit_price': asset.price_unit,
            'uom_id': asset.uom_id.id,
            'is_generated': True
        }

    def get_equipment(self, equ):
        return {
            'project_scope': equ.project_scope.id,
            'section_name': equ.section_name.id,
            'variable_ref': equ.variable_ref.id,
            'product_id': equ.product_id.id,
            'description': equ.description,
            'group_of_product': equ.group_of_product.id,
            'cur_qty': equ.budgeted_qty_left,
            'cur_unit_price': equ.price_unit,
            'adj_unit_price': equ.price_unit,
            'uom_id': equ.uom_id.id,
            'cur_amt': equ.budgeted_amt_left,
            'is_generated': True
        }

    def get_subcon(self, sub):
        return {
            'project_scope': sub.project_scope.id,
            'section_name': sub.section_name.id,
            'variable_ref': sub.variable_ref.id,
            'variable': sub.variable.id,
            'description': sub.description,
            'cur_qty': sub.budgeted_qty_left,
            'cur_unit_price': sub.price_unit,
            'adj_unit_price': sub.price_unit,
            'uom_id': sub.uom_id.id,
            'cur_amt': sub.budgeted_amt_left,
            'is_generated': True
        }

    def get_material_bud(self, mat):
        return {
            'project_scope': mat.project_scope.id,
            'section_name': mat.section_name.id,
            'variable_ref': mat.variable.id,
            'product_id': mat.product_id.id,
            'description': mat.description,
            'group_of_product': mat.group_of_product.id,
            'cur_qty': mat.qty_left,
            'cur_unit_price': mat.amount,
            'adj_unit_price': mat.amount,
            'uom_id': mat.uom_id.id,
            'cur_amt': mat.amt_left,
            'is_generated': True
        }

    def get_labour_bud(self, lab):
        return {
            'project_scope': lab.project_scope.id,
            'section_name': lab.section_name.id,
            'variable_ref': lab.variable.id,
            'product_id': lab.product_id.id,
            'description': lab.description,
            'group_of_product': lab.group_of_product.id,
            'cur_qty': lab.qty_left,
            'cur_time': lab.time_left,
            'cur_contractors': lab.contractors,
            'cur_unit_price': lab.amount,
            'adj_unit_price': lab.amount,
            'uom_id': lab.uom_id.id,
            'cur_amt': lab.amt_left,
            'is_generated': True
        }

    def get_overhead_bud(self, ove):
        return {
            'project_scope': ove.project_scope.id,
            'section_name': ove.section_name.id,
            'variable_ref': ove.variable.id,
            'product_id': ove.product_id.id,
            'description': ove.description,
            'overhead_catagory': ove.overhead_catagory,
            'group_of_product': ove.group_of_product.id,
            'cur_qty': ove.qty_left,
            'cur_unit_price': ove.amount,
            'adj_unit_price': ove.amount,
            'uom_id': ove.uom_id.id,
            'cur_amt': ove.amt_left,
            'is_generated': True
        }

    def get_internal_asset_bud(self, asset):
        return {
            'project_scope': asset.project_scope_line_id.id,
            'section_name': asset.section_name.id,
            'asset_category_id': asset.asset_category_id.id,
            'asset_id': asset.asset_id.id,
            'description': asset.cs_internal_asset_id.description,
            'cur_qty': asset.budgeted_qty_left,
            'cur_amt': asset.budgeted_amt_left,
            'cur_unit_price': asset.price_unit,
            'adj_unit_price': asset.price_unit,
            'uom_id': asset.uom_id.id,
            'is_generated': True
        }

    def get_equipment_bud(self, equ):
        return {
            'project_scope': equ.project_scope.id,
            'section_name': equ.section_name.id,
            'variable_ref': equ.variable.id,
            'product_id': equ.product_id.id,
            'description': equ.description,
            'group_of_product': equ.group_of_product.id,
            'cur_qty': equ.qty_left,
            'cur_unit_price': equ.amount,
            'adj_unit_price': equ.amount,
            'uom_id': equ.uom_id.id,
            'cur_amt': equ.amt_left,
            'is_generated': True
        }

    def get_subcon_bud(self, sub):
        return {
            'project_scope': sub.project_scope.id,
            'section_name': sub.section_name.id,
            'variable_ref': sub.variable_ref.id,
            'variable': sub.subcon_id.id,
            'description': sub.description,
            'cur_qty': sub.qty_left,
            'cur_unit_price': sub.amount,
            'adj_unit_price': sub.amount,
            'uom_id': sub.uom_id.id,
            'cur_amt': sub.amt_left,
            'is_generated': True
        }

    @api.onchange('job_sheet_id', 'project_budget')
    def get_from_cost_sheet(self):
        material = []
        subcon = []
        internal_asset = []
        equipment = []
        labour = []
        overhead = []
        project_scope = []
        section = []
        self.itb_change_line_ids = [(5, 0, 0)]
        self.itb_project_scope_ids = [(5, 0, 0)]
        self.itb_section_ids = [(5, 0, 0)]
        self.itb_material_line_ids = [(5, 0, 0)]
        self.itb_labour_line_ids = [(5, 0, 0)]
        self.itb_overhead_line_ids = [(5, 0, 0)]
        self.itb_internal_asset_line_ids = [(5, 0, 0)]
        self.itb_equipment_line_ids = [(5, 0, 0)]
        self.itb_subcon_line_ids = [(5, 0, 0)]
        for record in self:
            if record.is_project_transfer is False:
                if record.job_sheet_id:
                    for line in record.job_sheet_id.project_scope_cost_ids:
                        project_scope.append((0, 0, {
                            'project_scope_id': line.project_scope_id.id,
                            'is_generated': True,
                            'itb_id': record.id
                        }
                        ))
                    for line in record.job_sheet_id.section_cost_ids:
                        section.append((0, 0, {
                            'project_scope_id': line.project_scope_id.id,
                            'section_id': line.section_id.id,
                            'is_generated': True,
                            'itb_id': record.id
                        }
                        ))
                    self.write({
                        'itb_project_scope_ids': project_scope,
                        'itb_section_ids': section,

                    })
                if record.budgeting_period != 'project':
                    if record.project_budget:
                        for bud in record.project_budget:
                            for mat in bud.budget_material_ids:
                                material.append((0, 0, self.get_material_bud(mat)
                                                 ))
                            for asset in bud.budget_internal_asset_ids:
                                internal_asset.append((0, 0, self.get_internal_asset_bud(asset)))
                            for equ in bud.budget_equipment_ids:
                                equipment.append((0, 0, self.get_equipment_bud(equ)
                                                  ))
                            for lab in bud.budget_labour_ids:
                                labour.append((0, 0, self.get_labour_bud(lab)
                                               ))
                            for sub in bud.budget_subcon_ids:
                                subcon.append((0, 0, self.get_subcon_bud(sub)
                                               ))
                            for ove in bud.budget_overhead_ids:
                                overhead.append((0, 0, self.get_overhead_bud(ove)
                                                 ))
                        self.write({
                            'itb_material_line_ids': material,
                            'itb_subcon_line_ids': subcon,
                            'itb_internal_asset_line_ids': internal_asset,
                            'itb_equipment_line_ids': equipment,
                            'itb_labour_line_ids': labour,
                            'itb_overhead_line_ids': overhead,
                        })
                else:
                    if record.job_sheet_id:
                        for cos in record.job_sheet_id:
                            for mat in cos.material_ids:
                                material.append((0, 0, self.get_material(mat)
                                                 ))
                            for asset in cos.internal_asset_ids:
                                internal_asset.append((0, 0, self.get_internal_asset(asset)))
                            for equ in cos.material_equipment_ids:
                                equipment.append((0, 0, self.get_equipment(equ)
                                                  ))
                            for lab in cos.material_labour_ids:
                                labour.append((0, 0, self.get_labour(lab)
                                               ))
                            for sub in cos.material_subcon_ids:
                                subcon.append((0, 0, self.get_subcon(sub)
                                               ))
                            for ove in cos.material_overhead_ids:
                                overhead.append((0, 0, self.get_overhead(ove)
                                                 ))
                        self.write({
                            'itb_material_line_ids': material,
                            'itb_subcon_line_ids': subcon,
                            'itb_internal_asset_line_ids': internal_asset,
                            'itb_equipment_line_ids': equipment,
                            'itb_labour_line_ids': labour,
                            'itb_overhead_line_ids': overhead,
                        })




    @api.depends('project_id', 'job_sheet_id', 'itb_change_line_ids', 'itb_material_line_ids.adjusted',
                 'itb_labour_line_ids.adjusted', 'itb_internal_asset_line_ids.adjusted',
                 'itb_overhead_line_ids.adjusted', 'itb_equipment_line_ids.adjusted', 'itb_subcon_line_ids.adjusted')
    def _compute_free_amt(self):
        free_mat = 0.00
        free_lab = 0.00
        free_ove = 0.00
        free_asset = 0.00
        free_equ = 0.00
        free_sub = 0.00
        cost_free = 0.00

        for res in self:
            if res.project_id and res.job_sheet_id:
                for line in res.itb_material_line_ids:
                    free_mat += line.adjusted
                for line in res.itb_labour_line_ids:
                    free_lab += line.adjusted
                for line in res.itb_overhead_line_ids:
                    free_ove += line.adjusted
                for line in res.itb_internal_asset_line_ids:
                    free_asset += line.adjusted
                for line in res.itb_equipment_line_ids:
                    free_equ += line.adjusted
                for line in res.itb_subcon_line_ids:
                    free_sub += line.adjusted

                cost_free = res.job_sheet_id.amount_free

                change = (free_mat + free_lab + free_asset + free_ove + free_equ + free_sub)

                if not res.itb_change_line_ids:
                    res.free_amt = cost_free
                else:
                    res.change_amt = change * -1
                    free = cost_free + (change * -1)
                    res.free_amt = free

            else:
                res.free_amt = 0

    def send_table_material(self, line):
        for rec in self:
            if not rec.is_change_allocation:
                return {
                    'type': 'material',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'group_of_product': line.group_of_product.id,
                    'product_id': line.product_id.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': line.cur_qty,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': line.cal_qty,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'is_newly_added_product': line.is_newly_added_product,
                    'is_not_from_cost_sheet': line.is_not_from_cost_sheet
                }
            else:
                return {
                    'type': 'material',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'group_of_product': line.group_of_product.id,
                    'product_id': line.product_id.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': line.cur_qty,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': line.cal_qty,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'adj_qty': line.adj_qty,
                }

    def send_table_labour(self, line):
        for rec in self:
            if not rec.is_change_allocation:
                line._compute_cal_contractors()
                return {
                    'type': 'labour',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'group_of_product': line.group_of_product.id,
                    'product_id': line.product_id.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': 0,
                    'bfr_time': line.cur_time,
                    'bfr_contractors': line.cur_contractors,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': 0,
                    'aft_time': line.cal_time,
                    'aft_contractors': line.cal_contractors,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'is_newly_added_product': line.is_newly_added_product,
                    'is_not_from_cost_sheet': line.is_not_from_cost_sheet
                }
            else:
                line._compute_cal_contractors()
                return {
                    'type': 'labour',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'group_of_product': line.group_of_product.id,
                    'product_id': line.product_id.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': 0,
                    'bfr_time': line.cur_time,
                    'bfr_contractors': line.cur_contractors,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': 0,
                    'aft_time': line.cal_time,
                    'aft_contractors': line.cal_contractors,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'adj_qty': line.adj_qty,
                    'adj_time': line.adj_time,
                    'adj_contractors': line.adj_contractors,
                }

    def send_table_overhead(self, line):
        for rec in self:
            if not rec.is_change_allocation:
                return {
                    'type': 'overhead',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'overhead_catagory': line.overhead_catagory,
                    'group_of_product': line.group_of_product.id,
                    'product_id': line.product_id.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': line.cur_qty,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': line.cal_qty,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'is_newly_added_product': line.is_newly_added_product,
                    'is_not_from_cost_sheet': line.is_not_from_cost_sheet
                }
            else:
                return {
                    'type': 'overhead',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'overhead_catagory': line.overhead_catagory,
                    'group_of_product': line.group_of_product.id,
                    'product_id': line.product_id.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': line.cur_qty,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': line.cal_qty,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'adj_qty': line.adj_qty,
                }

    def send_table_internal_asset(self, line):
        for rec in self:
            if not rec.is_change_allocation:
                return {
                    'type': 'internal_asset',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'asset_category_id': line.asset_category_id.id,
                    'asset_id': line.asset_id.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': line.cur_qty,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': line.cal_qty,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'is_newly_added_product': line.is_newly_added_product,
                    'is_not_from_cost_sheet': line.is_not_from_cost_sheet
                }
            else:
                return {
                    'type': 'internal_asset',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'asset_category_id': line.asset_category_id.id,
                    'asset_id': line.asset_id.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': line.cur_qty,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': line.cal_qty,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'adj_qty': line.adj_qty,
                }

    def send_table_equipment(self, line):
        for rec in self:
            if not rec.is_change_allocation:
                return {
                    'type': 'equipment',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'group_of_product': line.group_of_product.id,
                    'product_id': line.product_id.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': line.cur_qty,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': line.cal_qty,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'is_newly_added_product': line.is_newly_added_product,
                    'is_not_from_cost_sheet': line.is_not_from_cost_sheet
                }
            else:
                return {
                    'type': 'equipment',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'group_of_product': line.group_of_product.id,
                    'product_id': line.product_id.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': line.cur_qty,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': line.cal_qty,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'adj_qty': line.adj_qty,
                }

    def send_table_subcon(self, line):
        for rec in self:
            if not rec.is_change_allocation:
                return {
                    'type': 'subcon',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'variable': line.variable.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': line.cur_qty,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': line.cal_qty,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'is_newly_added_product': line.is_newly_added_product,
                    'is_not_from_cost_sheet': line.is_not_from_cost_sheet
                }
            else:
                return {
                    'type': 'subcon',
                    'project_scope': line.project_scope.id,
                    'section_name': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'variable': line.variable.id,
                    'description': line.description,
                    'uom_id': line.uom_id.id,
                    'bfr_qty': line.cur_qty,
                    'bfr_unit_price': line.cur_unit_price,
                    'bfr_amt': line.cur_amt,
                    'aft_qty': line.cal_qty,
                    'aft_unit_price': line.adj_unit_price,
                    'aft_amt': line.adj_amt,
                    'free_amt': line.adjusted,
                    'adj_qty': line.adj_qty,
                }

    @api.onchange('itb_material_line_ids', 'itb_labour_line_ids', 'itb_overhead_line_ids', 'itb_equipment_line_ids',
                  'itb_subcon_line_ids', 'itb_internal_asset_line_ids')
    def _get_line_change(self):
        self.itb_change_line_ids = [(5, 0, 0)]
        for rec in self:
            for line in rec.itb_material_line_ids:
                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                    rec.itb_change_line_ids = [(0, 0, self.send_table_material(line))]
            for line in rec.itb_labour_line_ids:
                if line.adj_unit_price != line.cur_unit_price or line.adj_time != 0 or line.adj_contractors != 0:
                    rec.itb_change_line_ids = [(0, 0, self.send_table_labour(line))]
            for line in rec.itb_overhead_line_ids:
                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                    rec.itb_change_line_ids = [(0, 0, self.send_table_overhead(line))]
            for line in rec.itb_internal_asset_line_ids:
                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                    rec.itb_change_line_ids = [(0, 0, self.send_table_internal_asset(line))]
            for line in rec.itb_equipment_line_ids:
                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                    rec.itb_change_line_ids = [(0, 0, self.send_table_equipment(line))]
            for line in rec.itb_subcon_line_ids:
                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                    rec.itb_change_line_ids = [(0, 0, self.send_table_subcon(line))]

    def update_material(self, line):
        return {
            'product_qty': line.cal_cs_qty,
            'price_unit': line.adj_unit_price,
        }

    def update_material_cs(self, line, all_qty, all_mmt, cost_sheet_line):
        return {
            'product_qty': cost_sheet_line.product_qty + line.adj_qty,
            'price_unit': line.adj_unit_price,
            'allocated_budget_qty': all_qty,
            'allocated_budget_amt': all_mmt,
        }

    def update_labour_cs(self, line, all_time, all_contractors, all_mmt, cost_sheet_line):
        return {
            'time': cost_sheet_line.time + line.adj_time,
            'price_unit': line.adj_unit_price,
            'allocated_budget_time': all_time,
            'allocated_contractors': all_contractors,
            'allocated_budget_amt': all_mmt,
        }

    def update_material_bd(self, line):
        return {
            'quantity': line.cal_cs_qty,
            'amount': line.adj_unit_price,
        }

    def update_labour_bd(self, line):
        return {
            'time': line.cal_time,
            'contractors': line.cal_contractors,
        }

    def add_material(self, line):
        return {
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable_ref': line.variable_ref.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'description': line.description,
            'product_qty': line.cal_qty,
            'uom_id': line.uom_id.id,
            'price_unit': line.adj_unit_price,
        }

    def add_material_cs(self, line):
        return {
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable_ref': line.variable_ref.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'description': line.description,
            'product_qty': line.cal_qty,
            'uom_id': line.uom_id.id,
            'price_unit': line.adj_unit_price,
            'allocated_budget_qty': line.cal_qty,
            'allocated_budget_amt': line.adj_amt,
        }

    def add_labour_cs(self, line):
        return {
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable_ref': line.variable_ref.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'description': line.description,
            'product_qty': line.cal_qty,
            'time': line.cal_time,
            'contractors': line.cal_contractors,
            'uom_id': line.uom_id.id,
            'price_unit': line.adj_unit_price,
            'allocated_budget_qty': line.cal_qty,
            'allocated_budget_amt': line.adj_amt,
        }

    def add_overhead(self, line):
        return {
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable_ref': line.variable_ref.id,
            'overhead_catagory': line.overhead_catagory,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'description': line.description,
            'product_qty': line.cal_qty,
            'uom_id': line.uom_id.id,
            'price_unit': line.adj_unit_price,
        }

    def add_overhead_cs(self, line):
        return {
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable_ref': line.variable_ref.id,
            'overhead_catagory': line.overhead_catagory,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'description': line.description,
            'product_qty': line.cal_qty,
            'uom_id': line.uom_id.id,
            'price_unit': line.adj_unit_price,
            'allocated_budget_qty': line.cal_qty,
            'allocated_budget_amt': line.adj_amt,
        }

    def add_subcon(self, line):
        return {
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable_ref': line.variable_ref.id,
            'variable': line.variable.id,
            'description': line.description,
            'product_qty': line.cal_qty,
            'uom_id': line.uom_id.id,
            'price_unit': line.adj_unit_price,
        }

    def add_subcon_cs(self, line):
        return {
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable_ref': line.variable_ref.id,
            'variable': line.variable.id,
            'description': line.description,
            'product_qty': line.cal_qty,
            'uom_id': line.uom_id.id,
            'price_unit': line.adj_unit_price,
            'allocated_budget_qty': line.cal_qty,
            'allocated_budget_amt': line.adj_amt,
        }

    def add_subcon_bd(self, line):
        return {
            'cs_subcon_id': line.cs_subcon_id.id,
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable_ref': line.variable_ref.id,
            'subcon_id': line.variable.id,
            'description': line.description,
            'quantity': line.cal_qty,
            'uom_id': line.uom_id.id,
            'amount': line.adj_unit_price,
        }

    def add_material_bd(self, line):
        return {
            'cs_material_id': line.cs_material_id.id,
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable': line.variable_ref.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'description': line.description,
            'quantity': line.cal_qty,
            'uom_id': line.uom_id.id,
            'amount': line.adj_unit_price,
        }

    def add_labour_bd(self, line):
        return {
            'cs_labour_id': line.cs_labour_id.id,
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable': line.variable_ref.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'description': line.description,
            'quantity': line.cal_qty,
            'contractors': line.cal_contractors,
            'time': line.cal_time,
            'uom_id': line.uom_id.id,
            'amount': line.adj_unit_price,
        }

    def add_internal_asset_bd(self, line):
        return {
            'cs_internal_asset_id': line.cs_asset_id.id,
            'project_scope_line_id': line.project_scope.id,
            'section_name': line.section_name.id,
            'asset_category_id': line.asset_category_id.id,
            'asset_id': line.asset_id.id,
            # 'description': line.description,
            'budgeted_qty': line.cal_qty,
            'uom_id': line.uom_id.id,
            'price_unit': line.adj_unit_price,
        }

    def add_equipment_bd(self, line):
        return {
            'cs_equipment_id': line.cs_equipment_id.id,
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable': line.variable_ref.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'description': line.description,
            'quantity': line.cal_qty,
            'uom_id': line.uom_id.id,
            'amount': line.adj_unit_price,
        }

    def add_overhead_bd(self, line):
        return {
            'cs_overhead_id': line.cs_overhead_id.id,
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable': line.variable_ref.id,
            'overhead_catagory': line.overhead_catagory,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'description': line.description,
            'quantity': line.cal_qty,
            'uom_id': line.uom_id.id,
            'amount': line.adj_unit_price,
        }

    def update_itb_line(self, line):
        return {
            'type': line.type,
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable_ref': line.variable_ref.id,
            'overhead_category': line.overhead_catagory if line.type == 'overhead' else False,
            'asset_category_id': line.asset_category_id.id if line.type == 'internal_asset' else False,
            'group_of_product': line.group_of_product.id,
            'asset_id': line.asset_id.id if line.type == 'internal_asset' else False,
            'product_id': line.product_id.id,
            'variable': line.variable.id,
            'description': line.description,
            'uom_id': line.uom_id.id,
            'cur_qty': line.bfr_qty,
            'cur_time': line.bfr_time,
            'cur_contractors': line.bfr_contractors,
            'cur_unit_price': line.bfr_unit_price,
            'cur_amt': line.bfr_amt,
            'adj_qty': line.aft_qty,
            'adj_time': line.aft_time,
            'adj_contractors': line.aft_contractors,
            'adj_unit_price': line.aft_unit_price,
            'adj_amt': line.aft_amt,
            'adjusted': line.free_amt,
            'is_newly_added_product': line.is_newly_added_product,
            'is_not_from_cost_sheet': line.is_not_from_cost_sheet
        }

    def update_itb_history(self, rec):
        return {
            'date': datetime.now(),
            'itb_id': rec.id,
            'free_amt': rec.free_amt,
            'state': 'done',
        }

    def update_change_allocation_line(self, line):
        return {
            'type': line.type,
            'project_scope': line.project_scope.id,
            'section_name': line.section_name.id,
            'variable_ref': line.variable_ref.id,
            'overhead_category': line.overhead_catagory if line.type == 'overhead' else False,
            'asset_category_id': line.asset_category_id.id if line.type == 'internal_asset' else False,
            'group_of_product': line.group_of_product.id,
            'asset_id': line.asset_id.id if line.type == 'internal_asset' else False,
            'product_id': line.product_id.id,
            'variable': line.variable.id,
            'description': line.description,
            'uom_id': line.uom_id.id,
            'cur_qty': line.bfr_qty,
            'cur_time': line.bfr_time,
            'cur_contractors': line.bfr_contractors,
            'cur_unit_price': line.bfr_unit_price,
            'cur_amt': line.bfr_amt,
            'adj_qty': line.aft_qty,
            'adj_time': line.aft_time,
            'adj_contractors': line.aft_contractors,
            'adj_unit_price': line.aft_unit_price,
            'adj_amt': line.aft_amt,
            'adjusted': line.free_amt,
        }

    def update_change_allocation_line_history(self, rec):
        return {
            'date': datetime.now(),
            'itb_id': rec.id,
            'adjusted_amt': sum(self.itb_change_line_ids.mapped('free_amt')),
            'state': 'done',
        }

    def update_pbt_send_history(self, rec):
        return {
            'date': datetime.now(),
            'pbt_id': rec.id,
            'project_id': rec.project_id.id,
            'dest_project_id': rec.dest_project_id.id,
            'send_amount': rec.send_amt,
            'state': 'done',
        }

    def update_pbt_receive_history(self, rec):
        return {
            'date': datetime.now(),
            'pbt_id': rec.id,
            'project_id': rec.project_id.id,
            'dest_project_id': rec.dest_project_id.id,
            'allocation_amount': rec.send_amt,
            'state': 'done',
        }

    def update_bt_send_history(self, rec):
        return {
            'date': datetime.now(),
            'pbt_id': rec.id,
            'project_budget': rec.project_budget.id,
            'dest_project_budget': rec.dest_project_budget.id,
            'send_amount': rec.send_amt,
            'state': 'done',
        }

    def update_bt_receive_history(self, rec):
        return {
            'date': datetime.now(),
            'pbt_id': rec.id,
            'project_budget': rec.project_budget.id,
            'dest_project_budget': rec.dest_project_budget.id,
            'allocation_amount': rec.send_amt,
            'state': 'done',
        }

    def create_budget_bud_change_request(self):
        for record in self:
            context = {
                # 'default_is_project_budget': True,
                'default_project_id': record.project_id.id,
                'default_branch_id': record.branch_id.id,
                'default_project_budget': record.id,
                'default_is_project_transfer': False,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Change Budget Request',
                'view_mode': 'form',
                'res_model': 'internal.transfer.budget',
                'context': context,
                'target': 'current',
            }

    def confirm(self):
        for rec in self:
            # Project Budget Transfer
            if rec.is_project_transfer and not rec.is_change_allocation:
                amount = rec.free_amt - rec.send_amt
                if rec.free_amt < 0:
                    raise ValidationError(_("The available budget amount cannot below 0."))

                if amount < 0:
                    raise ValidationError(_("The allocation amount cannot greater than the available budget amount"))
                else:
                    rec.job_sheet_id.history_pbt_ids = [(0, 0, self.update_pbt_send_history(rec))]
                    rec.dest_job_sheet_id.history_pbt_ids = [(0, 0, self.update_pbt_receive_history(rec))]
                    rec.write({'state': 'done',
                               'approve_date': datetime.now(),
                               })

            # Change Allocation Request
            elif not rec.is_project_transfer and rec.is_change_allocation:
                if not rec.itb_change_line_ids:
                    raise ValidationError(_("You don't make any changes. Please make changes first"))

                if rec.check_quantity():
                    raise ValidationError(_("The adjusted quantity cannot greater than the unallocated quantity "
                                            "or less than current quantity"))

                for material in rec.itb_material_line_ids:
                    if material.adj_unit_price != material.cur_unit_price or material.adj_qty != 0:
                        if material.cs_material_id and material.bd_material_id:
                            rec.job_sheet_id.material_ids = [(1, material.cs_material_id.id, {
                                'allocated_budget_qty': material.cs_material_id.allocated_budget_qty + material.adj_qty,
                                'allocated_budget_amt': material.cs_material_id.allocated_budget_amt + material.adjusted,
                            })]

                            rec.project_budget.budget_material_ids = [
                                (1, material.bd_material_id.id, {
                                    'quantity': material.bd_material_id.quantity + material.adj_qty,
                                })]

                        elif material.cs_material_id and not material.bd_material_id:
                            rec.job_sheet_id.material_ids = [(1, material.cs_material_id.id, {
                                'allocated_budget_qty': material.cs_material_id.allocated_budget_qty + material.adj_qty,
                                'allocated_budget_amt': material.cs_material_id.allocated_budget_amt + material.adjusted,
                            })]

                            rec.project_budget.budget_material_ids = [(0, 0, self.add_material_bd(material))]

                        else:
                            raise ValidationError(_("This additional line on material tab is not on the cost sheet"))

                for labour in rec.itb_labour_line_ids:
                    if labour.adj_unit_price != labour.cur_unit_price or labour.adj_time != 0 or labour.adj_contractors != 0:
                        if labour.cs_labour_id and labour.bd_labour_id:
                            rec.job_sheet_id.material_labour_ids = [(1, labour.cs_labour_id.id, {
                                'allocated_contractors': labour.cs_labour_id.allocated_contractors + labour.adj_contractors,
                                'allocated_budget_time': labour.cs_labour_id.allocated_budget_time + labour.adj_time,
                                'allocated_budget_amt': labour.cs_labour_id.allocated_budget_amt + labour.adjusted,
                            })]

                            rec.project_budget.budget_labour_ids = [
                                (1, labour.bd_labour_id.id, {
                                    'contractors': labour.bd_labour_id.contractors + labour.adj_contractors,
                                    'time': labour.bd_labour_id.time + labour.adj_time,
                                    'quantity': labour.bd_labour_id.quantity + labour.adj_time,
                                })]

                        elif labour.cs_labour_id and not labour.bd_labour_id:
                            rec.job_sheet_id.material_labour_ids = [(1, labour.cs_labour_id.id, {
                                'allocated_contractors': labour.cs_labour_id.allocated_contractors + labour.adj_contractors,
                                'allocated_budget_time': labour.cs_labour_id.allocated_budget_time + labour.adj_time,
                                'allocated_budget_amt': labour.cs_labour_id.allocated_budget_amt + labour.adjusted,
                            })]

                            rec.project_budget.budget_labour_ids = [(0, 0, self.add_labour_bd(labour))]

                        else:
                            raise ValidationError(_("This additional line on labour tab is not on the cost sheet"))

                for overhead in rec.itb_overhead_line_ids:
                    if overhead.adj_unit_price != overhead.cur_unit_price or overhead.adj_qty != 0:
                        if overhead.cs_overhead_id and overhead.bd_overhead_id:
                            rec.job_sheet_id.material_overhead_ids = [(1, overhead.cs_overhead_id.id, {
                                'allocated_budget_qty': overhead.cs_overhead_id.allocated_budget_qty + overhead.adj_qty,
                                'allocated_budget_amt': overhead.cs_overhead_id.allocated_budget_amt + overhead.adjusted,
                            })]

                            rec.project_budget.budget_overhead_ids = [
                                (1, overhead.bd_overhead_id.id, {
                                    'quantity': overhead.bd_overhead_id.quantity + overhead.adj_qty,
                                })]

                        elif overhead.cs_overhead_id and not overhead.bd_overhead_id:
                            rec.job_sheet_id.material_overhead_ids = [(1, overhead.cs_overhead_id.id, {
                                'allocated_budget_qty': overhead.cs_overhead_id.allocated_budget_qty + overhead.adj_qty,
                                'allocated_budget_amt': overhead.cs_overhead_id.allocated_budget_amt + overhead.adjusted,
                            })]

                            rec.project_budget.budget_overhead_ids = [(0, 0, self.add_overhead_bd(overhead))]

                        else:
                            raise ValidationError(_("This additional line on overhead tab is not on the cost sheet"))

                for asset in rec.itb_internal_asset_line_ids:
                    if asset.adj_unit_price != asset.cur_unit_price or asset.adj_qty != 0:
                        if asset.cs_asset_id and asset.bd_asset_id:
                            rec.job_sheet_id.internal_asset_ids = [(1, asset.cs_asset_id.id, {
                                'allocated_budget_qty': asset.cs_asset_id.allocated_budget_qty + asset.adj_qty,
                                'allocated_budget_amt': asset.cs_asset_id.allocated_budget_amt + asset.adjusted,
                            })]

                            rec.project_budget.budget_internal_asset_ids = [
                                (1, asset.bd_asset_id.id, {
                                    'budgeted_qty': asset.bd_asset_id.budgeted_qty + asset.adj_qty,
                                })]

                        elif asset.cs_asset_id and not asset.bd_asset_id:
                            rec.job_sheet_id.internal_asset_ids = [(1, asset.cs_asset_id.id, {
                                'allocated_budget_qty': asset.cs_asset_id.allocated_budget_qty + asset.adj_qty,
                                'allocated_budget_amt': asset.cs_asset_id.allocated_budget_amt + asset.adjusted,
                            })]

                            rec.project_budget.budget_internal_asset_ids = [(0, 0, self.add_internal_asset_bd(asset))]

                        else:
                            raise ValidationError(
                                _("This additional line on Internal Asset tab is not on the cost sheet"))

                for equipment in rec.itb_equipment_line_ids:
                    if equipment.adj_unit_price != equipment.cur_unit_price or equipment.adj_qty != 0:
                        if equipment.cs_equipment_id and equipment.bd_equipment_id:
                            rec.job_sheet_id.material_equipment_ids = [(1, equipment.cs_equipment_id.id, {
                                'allocated_budget_qty': equipment.cs_equipment_id.allocated_budget_qty + equipment.adj_qty,
                                'allocated_budget_amt': equipment.cs_equipment_id.allocated_budget_amt + equipment.adjusted,
                            })]

                            rec.project_budget.budget_equipment_ids = [
                                (1, equipment.bd_equipment_id.id, {
                                    'quantity': equipment.bd_equipment_id.quantity + equipment.adj_qty,
                                })]

                        elif equipment.cs_equipment_id and not equipment.bd_equipment_id:
                            rec.job_sheet_id.material_equipment_ids = [(1, equipment.cs_equipment_id.id, {
                                'allocated_budget_qty': equipment.cs_equipment_id.allocated_budget_qty + equipment.adj_qty,
                                'allocated_budget_amt': equipment.cs_equipment_id.allocated_budget_amt + equipment.adjusted,
                            })]

                            rec.project_budget.budget_equipment_ids = [(0, 0, self.add_equipment_bd(equipment))]

                        else:
                            raise ValidationError(_("This additional line on equipment tab is not on the cost sheet"))

                for subcon in rec.itb_subcon_line_ids:
                    if subcon.adj_unit_price != subcon.cur_unit_price or subcon.adj_qty != 0:
                        if subcon.cs_subcon_id and subcon.bd_subcon_id:
                            rec.job_sheet_id.material_subcon_ids = [(1, subcon.cs_subcon_id.id, {
                                'allocated_budget_qty': subcon.cs_subcon_id.allocated_budget_qty + subcon.adj_qty,
                                'allocated_budget_amt': subcon.cs_subcon_id.allocated_budget_amt + subcon.adjusted,
                            })]

                            rec.project_budget.budget_subcon_ids = [
                                (1, subcon.bd_subcon_id.id, {
                                    'quantity': subcon.bd_subcon_id.quantity + subcon.adj_qty,
                                })]

                        elif subcon.cs_subcon_id and not subcon.bd_subcon_id:
                            rec.job_sheet_id.material_subcon_ids = [(1, subcon.cs_subcon_id.id, {
                                'allocated_budget_qty': subcon.cs_subcon_id.allocated_budget_qty + subcon.adj_qty,
                                'allocated_budget_amt': subcon.cs_subcon_id.allocated_budget_qty + subcon.adjusted,
                            })]

                            rec.project_budget.budget_subcon_ids = [(0, 0, self.add_subcon_bd(subcon))]

                        else:
                            raise ValidationError(_("This additional line on subcon tab is not on the cost sheet"))

                rec.job_sheet_id.change_allocation_line_history_cost_ids = [
                    (0, 0, self.update_change_allocation_line_history(rec))]
                rec.job_sheet_id.set_scope_section_table()
                rec.job_sheet_id.get_gop_material_table()
                rec.job_sheet_id.get_gop_labour_table()
                rec.job_sheet_id.get_gop_overhead_table()
                rec.job_sheet_id.get_gop_equipment_table()

                rec.project_budget.budget_change_allocation_history_ids = [
                    (0, 0, self.update_change_allocation_line_history(rec))]
                rec.project_budget.get_gop_material_table()
                rec.project_budget.get_gop_labour_table()
                rec.project_budget.get_gop_overhead_table()
                rec.project_budget.get_gop_equipment_table()

                rec.project_budget.budget_material_ids._get_id_from_cs()
                rec.project_budget.budget_labour_ids._get_id_from_cs()
                rec.project_budget.budget_overhead_ids._get_id_from_cs()
                rec.project_budget.budget_equipment_ids._get_id_from_cs()
                rec.project_budget.budget_subcon_ids._get_id_from_cs()

                for change in rec.itb_change_line_ids:
                    rec.project_budget.budget_change_allocation_line_ids = [
                        (0, 0, self.update_change_allocation_line(change))]
                    rec.job_sheet_id.change_allocation_line_cost_ids = [
                        (0, 0, self.update_change_allocation_line(change))]

                rec.write({'state': 'done',
                           'approve_date': datetime.now(),
                           })

            # Budget Change Request
            else:
                if rec.free_amt < 0 and not rec.is_continue_over_budget:
                    return {
                        'name': "Warning",
                        'view_mode': 'form',
                        'res_model': 'internal.transfer.budget.over.budget.validation',
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': {
                            'default_is_approval_matrix': False,
                            'default_warning_message': "Cost Sheet Budget will over the Contract Budget, "
                                               "are you sure want to continue?",
                            'default_itb_id': rec.id
                        }
                    }
                if not rec.itb_change_line_ids:
                    raise ValidationError(_("You don't make any changes. Please make changes first"))
                else:
                    all_qty = 0
                    all_mmt = 0
                    if rec.budgeting_period != 'project':
                        for line in rec.itb_project_scope_ids:
                            if not line.is_generated:
                                rec.project_id.write({
                                    'project_scope_ids': [(0, 0, {
                                        'project_scope': line.project_scope_id.id,
                                    })]
                                })
                                rec.project_budget.itb_line_bud_ids = [(0, 0, {
                                    # 'type': line.type,
                                    'project_scope': line.project_scope_id.id,
                                })]
                                rec.job_sheet_id.internal_transfer_budget_line_ids = [(0, 0, {
                                    # 'type': line.type,
                                    'project_scope': line.project_scope_id.id,
                                })]
                        for line in rec.itb_section_ids:
                            if not line.is_generated:
                                rec.project_id.write({
                                    'project_section_ids': [(0, 0, {
                                        'project_scope': line.project_scope_id.id,
                                        'section': line.section_id.id
                                    })]
                                })
                                rec.project_budget.itb_line_bud_ids = [(0, 0, {
                                    # 'type': line.type,
                                    'project_scope': line.project_scope_id.id,
                                    'section_name': line.section_id.id
                                })]
                                rec.job_sheet_id.internal_transfer_budget_line_ids = [(0, 0, {
                                    # 'type': line.type,
                                    'project_scope': line.project_scope_id.id,
                                    'section_name': line.section_id.id
                                })]
                        for line in rec.itb_material_line_ids:
                            if line.bd_material_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    rec.project_budget.budget_material_ids = [
                                        (1, line.bd_material_id.id, self.update_material_bd(line))]
                            else:
                                rec.project_budget.budget_material_ids = [(0, 0, self.add_material_bd(line))]

                            if line.cs_material_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    all_qty = line.cs_material_id.allocated_budget_qty + line.adj_qty
                                    all_mmt = line.cs_material_id.allocated_budget_amt + line.adjusted
                                    rec.job_sheet_id.material_ids = [
                                        (1, line.cs_material_id.id,
                                         self.update_material_cs(line, all_qty, all_mmt, line.cs_material_id))]
                            else:
                                rec.job_sheet_id.material_ids = [(0, 0, self.add_material_cs(line))]

                        for line in rec.itb_labour_line_ids:
                            if line.bd_labour_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_time != 0 or line.adj_contractors != 0:
                                    rec.project_budget.budget_labour_ids = [
                                        (1, line.bd_labour_id.id, self.update_labour_bd(line))]
                            else:
                                rec.project_budget.budget_labour_ids = [(0, 0, self.add_labour_bd(line))]

                            if line.cs_labour_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_time != 0 or line.adj_contractors != 0:
                                    all_time = line.cs_labour_id.allocated_budget_time + line.adj_time
                                    all_contractors = line.cs_labour_id.allocated_contractors + line.adj_contractors
                                    all_mmt = line.cs_labour_id.allocated_budget_amt + line.adjusted
                                    rec.job_sheet_id.material_labour_ids = [
                                        (1, line.cs_labour_id.id,
                                         self.update_labour_cs(line, all_time, all_contractors, all_mmt,
                                                               line.cs_labour_id))]
                            else:
                                rec.job_sheet_id.material_labour_ids = [(0, 0, self.add_labour_cs(line))]

                        for line in rec.itb_overhead_line_ids:
                            if line.bd_overhead_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    rec.project_budget.budget_overhead_ids = [
                                        (1, line.bd_overhead_id.id, self.update_material_bd(line))]
                            else:
                                rec.project_budget.budget_overhead_ids = [(0, 0, self.add_overhead_bd(line))]

                            if line.cs_overhead_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    all_qty = line.cs_overhead_id.allocated_budget_qty + line.adj_qty
                                    all_mmt = line.cs_overhead_id.allocated_budget_amt + line.adjusted
                                    rec.job_sheet_id.material_overhead_ids = [
                                        (1, line.cs_overhead_id.id,
                                         self.update_material_cs(line, all_qty, all_mmt, line.cs_overhead_id))]
                            else:
                                rec.job_sheet_id.material_overhead_ids = [(0, 0, self.add_overhead_cs(line))]

                        for line in rec.itb_internal_asset_line_ids:
                            if line.bd_asset_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    rec.project_budget.budget_internal_asset_ids = [
                                        (1, line.bd_asset_id.id, {'budgeted_qty': line.cal_cs_qty,
                                                                  'price_unit': line.adj_unit_price,
                                                                  })]
                            else:
                                rec.project_budget.budget_internal_asset_ids = [
                                    (0, 0, self.add_internal_asset_bd(line))]

                            if line.cs_asset_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    all_qty = line.cs_asset_id.allocated_budget_qty + line.adj_qty
                                    all_mmt = line.cs_asset_id.allocated_budget_amt + line.adjusted
                                    rec.job_sheet_id.internal_asset_ids = [
                                        (1, line.cs_asset_id.id, {
                                            'budgeted_qty': line.cs_asset_id.budgeted_qty + line.adj_qty,
                                            'price_unit': line.adj_unit_price,
                                            'allocated_budget_qty': all_qty,
                                            'allocated_budget_amt': all_mmt,
                                        })]
                                    line.cs_asset_id.onchange_quantity()
                                    line.cs_asset_id.job_sheet_id._amount_total()
                            else:
                                rec.job_sheet_id.internal_asset_ids = [(0, 0, {
                                    'project_scope': line.project_scope.id,
                                    'section_name': line.section_name.id,
                                    'variable_ref': line.variable_ref.id,
                                    'asset_category_id': line.asset_category_id.id,
                                    'asset_id': line.asset_id.id,
                                    'description': line.description,
                                    'product_qty': line.cal_qty,
                                    'uom_id': line.uom_id.id,
                                    'price_unit': line.adj_unit_price,
                                    'allocated_budget_qty': line.cal_qty,
                                    'allocated_budget_amt': line.adj_amt,
                                })]

                        for line in rec.itb_equipment_line_ids:
                            if line.bd_equipment_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    rec.project_budget.budget_equipment_ids = [
                                        (1, line.bd_equipment_id.id, self.update_material_bd(line))]
                            else:
                                rec.project_budget.budget_equipment_ids = [(0, 0, self.add_equipment_bd(line))]

                            if line.cs_equipment_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    all_qty = line.cs_equipment_id.allocated_budget_qty + line.adj_qty
                                    all_mmt = line.cs_equipment_id.allocated_budget_amt + line.adjusted
                                    rec.job_sheet_id.material_equipment_ids = [
                                        (1, line.cs_equipment_id.id,
                                         self.update_material_cs(line, all_qty, all_mmt, line.cs_equipment_id))]
                            else:
                                rec.job_sheet_id.material_equipment_ids = [(0, 0, self.add_material_cs(line))]

                        for line in rec.itb_subcon_line_ids:
                            if line.bd_subcon_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    rec.project_budget.budget_subcon_ids = [
                                        (1, line.bd_subcon_id.id, self.update_material_bd(line))]
                            else:
                                rec.project_budget.budget_subcon_ids = [(0, 0, self.add_subcon_bd(line))]

                            if line.cs_subcon_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    all_qty = line.cs_subcon_id.allocated_budget_qty + line.adj_qty
                                    all_mmt = line.cs_subcon_id.allocated_budget_amt + line.adjusted
                                    rec.job_sheet_id.material_subcon_ids = [
                                        (1, line.cs_subcon_id.id,
                                         self.update_material_cs(line, all_qty, all_mmt, line.cs_subcon_id))]
                            else:
                                rec.job_sheet_id.material_subcon_ids = [(0, 0, self.add_subcon_cs(line))]

                        for line in rec.itb_change_line_ids:
                            rec.project_budget.itb_line_bud_ids = [(0, 0, self.update_itb_line(line))]
                            rec.job_sheet_id.internal_transfer_budget_line_ids = [(0, 0, self.update_itb_line(line))]

                        rec.project_budget.history_itb_bud_ids = [(0, 0, self.update_itb_history(rec))]
                        rec.project_budget.get_gop_material_table()
                        rec.project_budget.get_gop_labour_table()
                        rec.project_budget.get_gop_overhead_table()
                        rec.project_budget.get_gop_equipment_table()

                        rec.project_budget.budget_material_ids._get_id_from_cs()
                        rec.project_budget.budget_labour_ids._get_id_from_cs()
                        rec.project_budget.budget_overhead_ids._get_id_from_cs()
                        rec.project_budget.budget_equipment_ids._get_id_from_cs()
                        rec.project_budget.budget_subcon_ids._get_id_from_cs()

                        rec.job_sheet_id.history_itb_ids = [(0, 0, self.update_itb_history(rec))]
                        rec.job_sheet_id.set_scope_section_table()
                        rec.job_sheet_id.get_gop_material_table()
                        rec.job_sheet_id.get_gop_labour_table()
                        rec.job_sheet_id.get_gop_overhead_table()
                        rec.job_sheet_id.get_gop_equipment_table()

                    else:
                        for line in rec.itb_project_scope_ids:
                            if not line.is_generated:
                                rec.project_id.write({
                                    'project_scope_ids': [(0, 0, {
                                        'project_scope': line.project_scope_id.id,
                                    })]
                                })
                                rec.project_budget.itb_line_bud_ids = [(0, 0, {
                                    # 'type': line.type,
                                    'project_scope': line.project_scope_id.id,
                                })]
                                rec.job_sheet_id.internal_transfer_budget_line_ids = [(0, 0, {
                                    # 'type': line.type,
                                    'project_scope': line.project_scope_id.id,
                                })]
                        for line in rec.itb_section_ids:
                            if not line.is_generated:
                                rec.project_id.write({
                                    'project_section_ids': [(0, 0, {
                                        'project_scope': line.project_scope_id.id,
                                        'section': line.section_id.id
                                    })]
                                })
                                rec.project_budget.itb_line_bud_ids = [(0, 0, {
                                    # 'type': line.type,
                                    'project_scope': line.project_scope_id.id,
                                    'section_name': line.section_id.id
                                })]
                                rec.job_sheet_id.internal_transfer_budget_line_ids = [(0, 0, {
                                    # 'type': line.type,
                                    'project_scope': line.project_scope_id.id,
                                    'section_name': line.section_id.id
                                })]
                        for line in rec.itb_material_line_ids:
                            if line.cs_material_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    rec.job_sheet_id.material_ids = [
                                        (1, line.cs_material_id.id, self.update_material(line))]
                            else:
                                rec.job_sheet_id.material_ids = [(0, 0, self.add_material(line))]

                        for line in rec.itb_labour_line_ids:
                            if line.cs_labour_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_time != 0 or line.adj_contractors != 0:
                                    rec.job_sheet_id.material_labour_ids = [
                                        (1, line.cs_labour_id.id, {
                                            'time': line.cs_labour_id.time + line.adj_time,
                                            'contractors': line.cs_labour_id.contractors + line.adj_contractors,
                                        })]
                            else:
                                rec.job_sheet_id.material_labour_ids = [(0, 0, {
                                    'project_scope': line.project_scope.id,
                                    'section_name': line.section_name.id,
                                    'variable_ref': line.variable_ref.id,
                                    'group_of_product': line.group_of_product.id,
                                    'product_id': line.product_id.id,
                                    'description': line.description,
                                    # 'product_qty': line.cal_qty,
                                    'time': line.cal_time,
                                    'contractors': line.cal_contractors,
                                    'uom_id': line.uom_id.id,
                                    'price_unit': line.adj_unit_price,
                                })]

                        for line in rec.itb_overhead_line_ids:
                            if line.cs_overhead_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    rec.job_sheet_id.material_overhead_ids = [
                                        (1, line.cs_overhead_id.id, self.update_material(line))]
                            else:
                                rec.job_sheet_id.material_overhead_ids = [(0, 0, self.add_overhead(line))]

                        for line in rec.itb_internal_asset_line_ids:
                            if line.cs_asset_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    rec.job_sheet_id.internal_asset_ids = [
                                        (1, line.cs_asset_id.id, {
                                            'budgeted_qty': line.cs_asset_id.budgeted_qty + line.adj_qty,
                                            'price_unit': line.adj_unit_price,
                                        })]
                            else:
                                rec.job_sheet_id.internal_asset_ids = [(0, 0, {
                                    'project_scope': line.project_scope.id,
                                    'section_name': line.section_name.id,
                                    'variable_ref': line.variable_ref.id,
                                    'asset_category_id': line.asset_category_id.id,
                                    'asset_id': line.asset_id.id,
                                    'description': line.description,
                                    'product_qty': line.cal_qty,
                                    'uom_id': line.uom_id.id,
                                    'price_unit': line.adj_unit_price,
                                })]

                        for line in rec.itb_equipment_line_ids:
                            if line.cs_equipment_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    rec.job_sheet_id.material_equipment_ids = [
                                        (1, line.cs_equipment_id.id, self.update_material(line))]
                            else:
                                rec.job_sheet_id.material_equipment_ids = [(0, 0, self.add_material(line))]

                        for line in rec.itb_subcon_line_ids:
                            if line.cs_subcon_id:
                                if line.adj_unit_price != line.cur_unit_price or line.adj_qty != 0:
                                    rec.job_sheet_id.material_subcon_ids = [
                                        (1, line.cs_subcon_id.id, self.update_material(line))]
                            else:
                                rec.job_sheet_id.material_subcon_ids = [(0, 0, self.add_subcon(line))]

                        for line in rec.itb_change_line_ids:
                            rec.job_sheet_id.internal_transfer_budget_line_ids = [(0, 0, self.update_itb_line(line))]

                        rec.job_sheet_id.history_itb_ids = [(0, 0, self.update_itb_history(rec))]
                        rec.job_sheet_id.set_scope_section_table()
                        rec.job_sheet_id.get_gop_material_table()
                        rec.job_sheet_id.get_gop_labour_table()
                        rec.job_sheet_id.get_gop_overhead_table()
                        rec.job_sheet_id.get_gop_equipment_table()

                    rec.write({'state': 'done',
                               'approve_date': datetime.now(),
                               })

    def unlink(self):
        for res in self:
            if res.state == 'approved':
                raise UserError(_('In order to delete this record, you must cancel it first.'))
            elif res.state == 'done':
                raise UserError(_('Cannot delete this record because the state is done.'))
        return super(BudgetChangeRequest, self).unlink()

    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines",
                                              compute='get_scope_lines')

    @api.depends('itb_project_scope_ids')
    def get_scope_lines(self):
        for rec in self:
            # pro = rec.project_id
            scope_ids = []
            for line in rec.itb_project_scope_ids:
                if line.project_scope_id:
                    scope_ids.append(line.project_scope_id._origin.id)
            rec.project_scope_computed = [(6, 0, scope_ids)]

    @api.onchange('itb_project_scope_ids')
    def _onchange_itb_project_scope_ids(self):
        """
        If changed scope doesn't exist in any estimate tab, then delete the lines
        This method has two approach:
        1. If the record is saved to database, then use _origin
        2. If the record is new, then use id
        """
        for rec in self:
            changed_scope = list()
            scope_list = list()
            if len(rec.itb_project_scope_ids) > 0 or len(rec._origin.itb_section_ids._origin) > 0:
                for scope in rec.itb_project_scope_ids:
                    # If BOQ record saved to database, use origin
                    # If new, then use id
                    scope_list.append(scope.project_scope_id.id)
                    if scope._origin.project_scope_id._origin.id:
                        if scope.project_scope_id.id != scope._origin.project_scope_id._origin.id:
                            changed_scope.append(scope._origin.project_scope_id._origin.id)
                    else:
                        changed_scope.append(scope.project_scope_id.id)
            if len(rec.itb_section_ids) > 0:
                for section in rec.itb_section_ids:
                    if section.project_scope_id.id in changed_scope:
                        rec.itb_section_ids = [(2, section._origin.id, 0)]
                    elif section.project_scope_id.id not in scope_list:
                        rec.itb_section_ids = [(2, section.id, 0)]

    @api.onchange('itb_section_ids')
    def _onchange_itb_section_ids(self):
        """
        If changed section doesn't exist in any estimate tab, then delete the lines
        This method has two approach:
        1. If the record is saved to database, then use _origin
        2. If the record is new, then use id
        """
        for rec in self:
            changed_section = list()
            section_list = list()
            if len(rec.itb_section_ids) > 0 or len(rec._origin.itb_section_ids._origin):
                for section in rec.itb_section_ids:
                    # same logic as _onchange_project_scope
                    section_list.append(section.section_id.id)
                    if section._origin.section_id._origin.id:
                        if section.section_id.id != section._origin.section_id._origin.id:
                            changed_section.append(section._origin.section_id._origin.id)
                    else:
                        changed_section.append(section.section_id.id)
            for material in rec.itb_material_line_ids:
                if material.section_name.id in changed_section:
                    rec.itb_material_line_ids = [(2, material._origin.id, 0)]
                elif material.section_name.id not in section_list:
                    rec.itb_material_line_ids = [(2, material.id, 0)]
            for labour in rec.itb_labour_line_ids:
                if labour.section_name.id in changed_section:
                    rec.itb_labour_line_ids = [(2, labour._origin.id, 0)]
                elif labour.section_name.id not in section_list:
                    rec.itb_labour_line_ids = [(2, labour.id, 0)]
            for overhead in rec.itb_overhead_line_ids:
                if overhead.section_name.id in changed_section:
                    rec.itb_overhead_line_ids = [(2, overhead._origin.id, 0)]
                elif overhead.section_name.id not in section_list:
                    rec.itb_overhead_line_ids = [(2, overhead.id, 0)]
            for internal in rec.itb_internal_asset_line_ids:
                if internal.section_name.id in changed_section:
                    rec.itb_internal_asset_line_ids = [(2, internal._origin.id, 0)]
                elif internal.section_name.id not in section_list:
                    rec.itb_internal_asset_line_ids = [(2, internal.id, 0)]
            for equipment in rec.itb_equipment_line_ids:
                if equipment.section_name.id in changed_section:
                    rec.itb_equipment_line_ids = [(2, equipment._origin.id, 0)]
                elif equipment.section_name.id not in section_list:
                    rec.itb_equipment_line_ids = [(2, equipment.id, 0)]
            for subcon in rec.itb_subcon_line_ids:
                if subcon.section_name.id in changed_section:
                    rec.itb_subcon_line_ids = [(2, subcon._origin.id, 0)]
                elif subcon.section_name.id not in section_list:
                    rec.itb_subcon_line_ids = [(2, subcon.id, 0)]


class BudgetChangeApproverUser(models.Model):
    _name = 'budget.change.approver.user'
    _description = 'Budget Change Approver User'

    budget_change_approver_id = fields.Many2one('internal.transfer.budget', string="Budget Change")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'budget_change_app_emp_ids', string="Approved user")
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
    matrix_user_ids = fields.Many2many('res.users', 'change_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    # parent status
    state = fields.Selection(related='budget_change_approver_id.state', string='Parent Status')

    @api.depends('budget_change_approver_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.budget_change_approver_id.budget_change_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len(rec.user_ids) < rec.minimum_approver and rec.budget_change_approver_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.budget_change_approver_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids


class ITBChangelLine(models.Model):
    _name = 'internal.transfer.budget.change.line'
    _description = 'Internal Transfer Budget Change Line'
    _order = 'id,sequence'

    itb_id = fields.Many2one('internal.transfer.budget', string="Internal Transfer Budget", ondelete='cascade')
    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    type = fields.Selection(
        [('material', 'Material'), ('labour', 'Labour'), ('overhead', 'Overhead'), ('equipment', 'Equipment'),
         ('internal_asset', 'Internal Asset'), ('subcon', 'Subcon')], string="Type", readonly=True, Store="1")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    overhead_catagory = fields.Selection([
        ('product', 'Product'),
        ('petty cash', 'Petty Cash'),
        ('cash advance', 'Cash Advance'),
        ('fuel', 'Fuel'),
    ], string='Overhead Catagory')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category')
    product_id = fields.Many2one('product.product', string='Product')
    variable = fields.Many2one('variable.template', string='Job Subcon')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    bfr_qty = fields.Float('Before quantity', default=0.00)
    bfr_time = fields.Float('Before Time', default=0.00)
    bfr_contractors = fields.Float('Before Contractors', default=0.00)
    bfr_unit_price = fields.Float('Before Unit Price', default=0.00)
    bfr_amt = fields.Float('Before Amount', default=0.00)
    aft_qty = fields.Float('After Quantity', default=0.00)
    aft_time = fields.Float('After Time', default=0.00)
    aft_contractors = fields.Float('After Contractors', default=0.00)
    aft_unit_price = fields.Float('After Unit Price', default=0.00)
    aft_amt = fields.Float('After Amount', default=0.00)
    free_amt = fields.Float('Adjusted', default=0.00)
    adj_qty = fields.Float('Adjusted Quantity', default=0.00)
    adj_time = fields.Float('Adjusted Time', default=0.00)
    adj_contractors = fields.Float('Adjusted Contractors', default=0.00)
    project_budget = fields.Many2many('project.budget', string='Periodical Budget', compute="_get_budget_project")
    # table
    project_budget_ids = fields.One2many('project.budget.change.line', 'change_line_id', string='Periodical Budget')

    project_id = fields.Many2one(related='itb_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    is_newly_added_product = fields.Boolean('Is newly added product')
    is_not_from_cost_sheet = fields.Boolean('Is not from cost sheet')

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                for line in rec.itb_id.itb_section_ids:
                    if rec.project_scope._origin.id == line.project_scope_id._origin.id:
                        section.append(line.section_id._origin.id)
            rec.project_section_computed = [(6, 0, section)]
            #     else:
            #         rec.project_section_computed = [(6, 0, [])]
            # else:
            #     rec.project_section_computed = [(6, 0, [])]

    @api.depends('itb_id.itb_change_line_ids', 'itb_id.itb_change_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.itb_id.itb_change_line_ids:
                no += 1
                l.sr_no = no

    def _get_material(self, line):
        return {
            'month': line.budget_id.month,
            'project_budget': line.budget_id.id,
            'bd_material_id': line.id,
            'bfr_qty': line.quantity,
        }

    def _get_labour(self, line):
        return {
            'month': line.budget_id.month,
            'project_budget': line.budget_id.id,
            'bd_labour_id': line.id,
            'bfr_qty': line.quantity,
        }

    def _get_overhead(self, line):
        return {
            'month': line.budget_id.month,
            'project_budget': line.budget_id.id,
            'bd_overhead_id': line.id,
            'bfr_qty': line.quantity,
        }

    def _get_internal_asset(self, line):
        return {
            'month': line.budget_id.month,
            'project_budget': line.budget_id.id,
            'bd_asset_id': line.id,
            'bfr_qty': line.budgeted_qty,
        }

    def _get_equipment(self, line):
        return {
            'month': line.budget_id.month,
            'project_budget': line.budget_id.id,
            'bd_equipment_id': line.id,
            'bfr_qty': line.quantity,
        }

    def _get_subcon(self, line):
        return {
            'month': line.budget_id.month,
            'project_budget': line.budget_id.id,
            'bd_subcon_id': line.id,
            'bfr_qty': line.quantity,
        }

    def _get_budget_project(self):
        for res in self:
            project_budget = res.env['project.budget'].search([('project_id', '=', res.itb_id.project_id.id)])
            res.project_budget = project_budget

    @api.depends('itb_id.itb_change_line_ids', 'itb_id.itb_change_line_ids', 'itb_id.itb_material_line_ids',
                 'itb_id.itb_labour_line_ids', 'itb_id.itb_overhead_line_ids', 'itb_id.itb_equipment_line_ids',
                 'itb_id.itb_internal_asset_line_ids', 'itb_id.itb_subcon_line_ids')
    def _get_budget_project_line(self):
        for res in self:
            if res.itb_id.is_project_budget == False:
                res.project_budget_ids = [(5, 0, 0)]
                for bud in res.project_budget:
                    if res.type == 'material':
                        for line in bud.budget_material_ids:
                            if line.project_scope == res.project_scope and line.section_name == res.section_name and line.variable == res.variable_ref and line.group_of_product == res.group_of_product and line.product_id == res.product_id:
                                res.project_budget_ids = [(0, 0, self._get_material(line))]
                    elif res.type == 'labour':
                        for line in bud.budget_labour_ids:
                            if line.project_scope == res.project_scope and line.section_name == res.section_name and line.variable == res.variable_ref and line.group_of_product == res.group_of_product and line.product_id == res.product_id:
                                res.project_budget_ids = [(0, 0, self._get_labour(line))]
                    elif res.type == 'overhead':
                        for line in bud.budget_overhead_ids:
                            if line.project_scope == res.project_scope and line.section_name == res.section_name and line.variable == res.variable_ref and line.group_of_product == res.group_of_product and line.product_id == res.product_id:
                                res.project_budget_ids = [(0, 0, self._get_overhead(line))]
                    elif res.type == 'internal_asset':
                        for line in bud.budget_internal_asset_ids:
                            if line.project_scope_line_id == res.project_scope and line.section_name == res.section_name and line.asset_category_id == res.asset_category_id and line.asset_id == res.asset_id:
                                res.project_budget_ids = [(0, 0, self._get_internal_asset(line))]
                    elif res.type == 'equipment':
                        for line in bud.budget_equipment_ids:
                            if line.project_scope == res.project_scope and line.section_name == res.section_name and line.variable == res.variable_ref and line.group_of_product == res.group_of_product and line.product_id == res.product_id:
                                res.project_budget_ids = [(0, 0, self._get_equipment(line))]
                    elif res.type == 'subcon':
                        for line in bud.budget_subcon_ids:
                            if line.project_scope == res.project_scope and line.section_name == res.section_name and line.subcon_id == res.variable:
                                res.project_budget_ids = [(0, 0, self._get_subcon(line))]
                    else:
                        raise ValidationError(_("Type is empty."))

    def revert_itb_change_line_ids(self):
        adj_qty = 0.00
        for rec in self:
            if rec.type == 'material':
                material = rec.env['internal.transfer.budget.material.line'].search(
                    [('itb_id', '=', self.itb_id.id), ('project_scope', '=', self.project_scope.id),
                     ('section_name', '=', self.section_name.id), ('variable_ref', '=', self.variable_ref.id),
                     ('group_of_product', '=', self.group_of_product.id), ('product_id', '=', self.product_id.id)])
                if material:
                    material.adj_qty = adj_qty
                    material.adj_unit_price = material.cur_unit_price
                    material.is_delete = False
            elif rec.type == 'labour':
                labour = rec.env['internal.transfer.budget.labour.line'].search(
                    [('itb_id', '=', self.itb_id.id), ('project_scope', '=', self.project_scope.id),
                     ('section_name', '=', self.section_name.id), ('variable_ref', '=', self.variable_ref.id),
                     ('group_of_product', '=', self.group_of_product.id), ('product_id', '=', self.product_id.id)])
                if labour:
                    labour.adj_qty = adj_qty
                    labour.adj_unit_price = labour.cur_unit_price
                    labour.is_delete = False
            elif rec.type == 'overhead':
                overhead = rec.env['internal.transfer.budget.overhead.line'].search(
                    [('itb_id', '=', self.itb_id.id), ('project_scope', '=', self.project_scope.id),
                     ('section_name', '=', self.section_name.id), ('variable_ref', '=', self.variable_ref.id),
                     ('group_of_product', '=', self.group_of_product.id), ('product_id', '=', self.product_id.id)])
                if overhead:
                    overhead.adj_qty = adj_qty
                    overhead.adj_unit_price = overhead.cur_unit_price
                    overhead.is_delete = False
            elif rec.type == 'internal_asset':
                asset = rec.env['internal.transfer.budget.internal.asset.line'].search(
                    [('itb_id', '=', self.itb_id.id), ('project_scope', '=', self.project_scope.id),
                     ('section_name', '=', self.section_name.id), ('variable_ref', '=', self.variable_ref.id),
                     ('asset_category_id', '=', self.asset_category_id.id), ('asset_id', '=', self.asset_id.id)])
                if asset:
                    asset.adj_qty = adj_qty
                    asset.adj_unit_price = asset.cur_unit_price
                    asset.is_delete = False
            elif rec.type == 'equipment':
                equipment = rec.env['internal.transfer.budget.equipment.line'].search(
                    [('itb_id', '=', self.itb_id.id), ('project_scope', '=', self.project_scope.id),
                     ('section_name', '=', self.section_name.id), ('variable_ref', '=', self.variable_ref.id),
                     ('group_of_product', '=', self.group_of_product.id), ('product_id', '=', self.product_id.id)])
                if equipment:
                    equipment.adj_qty = adj_qty
                    equipment.adj_unit_price = equipment.cur_unit_price
                    equipment.is_delete = False
            elif rec.type == 'subcon':
                subcon = rec.env['internal.transfer.budget.subcon.line'].search(
                    [('itb_id', '=', self.itb_id.id), ('project_scope', '=', self.project_scope.id),
                     ('section_name', '=', self.section_name.id), ('variable_ref', '=', self.variable_ref.id),
                     ('variable', '=', self.variable.id)])
                if subcon:
                    subcon.adj_qty = adj_qty
                    subcon.adj_unit_price = subcon.cur_unit_price
                    subcon.is_delete = False

            rec.itb_id._get_line_change()


class ProjectBudgetChange(models.Model):
    _name = 'project.budget.change.line'
    _description = 'Project Budget Change Line'
    _order = 'id, sequence'

    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    change_line_id = fields.Many2one('internal.transfer.budget.change.line', string="Internal Transfer Budget Line",
                                     ondelete='cascade')
    project_budget = fields.Many2one('project.budget', string='Project Budget')
    month = fields.Many2one('budget.period.line')
    bd_material_id = fields.Many2one('budget.material', 'BD Material ID')
    bd_labour_id = fields.Many2one('budget.labour', 'BD Labour ID')
    bd_overhead_id = fields.Many2one('budget.overhead', 'BD Overhead ID')
    bd_equipment_id = fields.Many2one('budget.equipment', 'BD Equipment ID')
    bd_subcon_id = fields.Many2one('budget.subcon', 'BD Subcon ID')
    bfr_qty = fields.Float('Before Quantity', default=0.00)
    aft_qty = fields.Float('After Quantity', default=0.00, Store="1")

    @api.depends('change_line_id.project_budget_ids', 'change_line_id.project_budget_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.change_line_id.project_budget_ids:
                no += 1
                l.sr_no = no


class ITBMaterialLine(models.Model):
    _name = 'internal.transfer.budget.material.line'
    _description = 'Internal Transfer Budget Material Line'
    _order = 'id,sequence'

    itb_id = fields.Many2one('internal.transfer.budget', string="Internal Transfer Budget", ondelete='cascade')
    job_sheet_id = fields.Many2one(related='itb_id.job_sheet_id', string="Cost Sheet")
    project_budget = fields.Many2one(related='itb_id.project_budget', string='Periodical Budget')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    cs_material_id = fields.Many2one('material.material', 'CS Material ID', compute='_get_cs_id')
    bd_material_id = fields.Many2one('budget.material', 'BD Material ID', compute='_get_bd_id')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    cur_qty = fields.Float('Current Quantity', default=0.00)
    adj_qty = fields.Float('Quantity', default=0.00)
    unallocated_qty = fields.Float(related='cs_material_id.product_qty_na')
    unallocated_amt = fields.Float(related='cs_material_id.product_amt_na')
    cal_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_qty")
    cal_cs_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_cs_qty")
    cur_unit_price = fields.Float('Current Unit price', default=0.00)
    adj_unit_price = fields.Float('Adjusted Unit price', default=0.00)
    cur_amt = fields.Float('Current Amount', default=0.00)
    adj_amt = fields.Float('Amount', default=0.00, compute="_compute_adjusted")
    adjusted = fields.Float('Adjusted', default=0.00, compute="_compute_adjusted")
    is_delete = fields.Boolean(string='Deleted', default=False)
    project_id = fields.Many2one(related='itb_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    is_newly_added_product = fields.Boolean('Is newly added product', compute="_compute_is_newly_added_product",
                                            store=True)
    is_change_allocation = fields.Boolean(related='itb_id.is_change_allocation', string='Is Change Allocation')
    is_generated = fields.Boolean('is generated', default=False)
    is_not_from_cost_sheet = fields.Boolean('Is not from cost sheet', compute='_compute_is_not_from_cost_sheet',
                                            store=True)
    adj_unallocated_qty = fields.Float('Adjusted Unallocated Quantity', default=0.00,
                                       compute="_compute_adjusted_unallocated_qty")
    adj_unallocated_amt = fields.Float('Adjusted Unallocated Amount', default=0.00,
                                       compute="_compute_adjusted_unallocated_amt")

    @api.depends('adj_qty', 'unallocated_qty')
    def _compute_adjusted_unallocated_qty(self):
        for rec in self:
            rec.adj_unallocated_qty = rec.unallocated_qty + (rec.adj_qty * -1)

    @api.depends('adj_qty', 'unallocated_amt')
    def _compute_adjusted_unallocated_amt(self):
        for rec in self:
            rec.adj_unallocated_amt = rec.adj_unallocated_qty * rec.cur_unit_price

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _compute_is_newly_added_product(self):
        for rec in self:
            is_newly_added_product = False
            line_required_data = [rec.project_scope.id, rec.section_name.id, rec.group_of_product.id, rec.product_id.id]

            if rec.project_budget and not rec.is_generated and False not in line_required_data:
                budget_change = rec.project_scope.name + rec.section_name.name + rec.group_of_product.name + \
                                rec.product_id.name
                periodical_budget = [
                    i.project_scope.name + i.section_name.name + i.group_of_product.name + i.product_id.name for i
                    in rec.project_budget.budget_material_ids]

                if budget_change not in periodical_budget:
                    is_newly_added_product = True
            rec.is_newly_added_product = is_newly_added_product

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _get_cs_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product and res.product_id:
                # line = self.env['material.material'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id),
                #      ('product_id', '=', res.product_id.id)], limit=1)
                line = res.itb_id.job_sheet_id.material_ids.filtered(lambda x: x.project_scope == res.project_scope and
                                                                               x.section_name == res.section_name and
                                                                               x.group_of_product == res.group_of_product
                                                                               and x.product_id == res.product_id)
                if line:
                    res.cs_material_id = line.id
                else:
                    res.cs_material_id = False
            else:
                res.cs_material_id = False

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _get_bd_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product and res.product_id:
                # line = self.env['budget.material'].search(
                #     [('budget_id', '=', res.project_budget.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id),
                #      ('product_id', '=', res.product_id.id)], limit=1)
                line = res.project_budget.budget_material_ids.filtered(
                    lambda x: x.project_scope == res.project_scope and
                              x.section_name == res.section_name and
                              x.group_of_product == res.group_of_product
                              and x.product_id == res.product_id)
                if line:
                    res.bd_material_id = line.id
                else:
                    res.bd_material_id = False
            else:
                res.bd_material_id = False

    @api.depends('product_id')
    def _compute_is_not_from_cost_sheet(self):
        for rec in self:
            is_not_from_cost_sheet = False
            if not rec.cs_material_id:
                is_not_from_cost_sheet = True
            rec.is_not_from_cost_sheet = is_not_from_cost_sheet

    #@api.onchange('product_id')
    #def line_validation(self):
    #    for rec in self:
    #        if rec.product_id:
    #            if not rec.cs_material_id:
    #                rec._get_cs_id()
    #                if rec.project_budget.budgeting_method == 'product_budget' and not rec.cs_material_id:
    #                    raise ValidationError(_("You're not allowed to add new product that is not from "
    #                                            "cost sheet in this budgeting method."))
    #                elif (rec.project_budget.budgeting_method == 'product_budget' and not rec.bd_material_id
    #                      and rec.is_newly_added_product and rec.is_change_allocation):
    #                    if rec.unallocated_qty == 0:
    #                        raise ValidationError(_("You're not allowed to add new product that is already "
    #                                                "allocated all its unallocated quantity to Periodical Budget."))
    #                elif rec.project_budget.budgeting_method == 'gop_budget':
    #                    if rec.group_of_product not in rec.project_budget.budget_material_ids.mapped(
    #                            'group_of_product'):
    #                        raise ValidationError(_("You're not allowed to add new group of product that is not "
    #                                                "from cost sheet in this budgeting method."))

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.adj_qty = 1
            self.adj_unit_price = self.cs_material_id.price_unit
            self.description = self.product_id.display_name
        else:
            self.uom_id = False
            self.adj_qty = False
            self.adj_unit_price = False
            self.description = False

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                for line in rec.itb_id.itb_section_ids:
                    if rec.project_scope._origin.id == line.project_scope_id._origin.id:
                        section.append(line.section_id._origin.id)
            rec.project_section_computed = [(6, 0, section)]

    @api.onchange('section_name')
    def _onchange_section_name(self):
        for rec in self:
            if rec.is_change_allocation:
                group_of_product = []
                if rec.section_name and rec.job_sheet_id:
                    for material in rec.job_sheet_id.material_ids:
                        if (material.group_of_product.id not in group_of_product and
                                material.section_name.id == rec.section_name.id):
                            group_of_product.append(material.group_of_product.id)
                return {
                    'domain': {'group_of_product': [('id', 'in', group_of_product)]}
                }

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product)]}
            }

    @api.depends('itb_id.itb_material_line_ids', 'itb_id.itb_material_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.itb_id.itb_material_line_ids:
                no += 1
                l.sr_no = no

    def _compute_cal_qty(self):
        for line in self:
            line.cal_qty = line.cur_qty + line.adj_qty

    def _compute_cal_cs_qty(self):
        for line in self:
            if line.bd_material_id:
                line.cal_cs_qty = line.bd_material_id.quantity + line.adj_qty
            else:
                line.cal_cs_qty = line.cs_material_id.product_qty + line.adj_qty

    @api.depends('adj_unit_price', 'adj_qty')
    def _compute_adjusted(self):
        qty = 0.00
        amt = 0.00
        adj = 0.00
        for line in self:
            check_qty = line.adj_qty + line.cur_qty

            if check_qty < 0:
                raise ValidationError(_("The adjusted quantity is over the remaining quantity."))
            elif line.adj_unit_price < 0:
                raise ValidationError(_("Adjusted amount cannot set below the current amount."))
            else:
                if line.adj_unit_price != line.cur_unit_price and line.adj_qty != 0:
                    qty = line.adj_qty + line.cur_qty
                    amt = qty * line.adj_unit_price
                elif line.adj_unit_price != line.cur_unit_price and line.adj_qty == 0:
                    qty = line.cur_qty
                    amt = line.cur_qty * line.adj_unit_price
                elif line.adj_qty != 0 and line.adj_unit_price == line.cur_unit_price:
                    qty = line.adj_qty + line.cur_qty
                    amt = qty * line.cur_unit_price
                else:
                    qty = line.cur_qty
                    amt = line.cur_amt
                # adj = amt - line.cur_amt
                if line.adj_unit_price != line.cur_unit_price:
                    if line.adj_qty == 0 and line.cur_qty == 0:
                        raise ValidationError(
                            _("You can't change the unit price if budget amount left is the return amount of your transaction."
                              "Please consider to use 'Claim Budget Left' on Cost Sheet or Periodical Budget in line's corresponding estimation tab."))
                    else:
                        adj = (line.cur_amt - (line.adj_qty + line.cur_qty) * line.adj_unit_price) * -1
                else:
                    adj = line.adj_qty * line.adj_unit_price

                line.write({'adj_amt': amt,
                            'adjusted': adj,
                            'cal_qty': check_qty,
                            })

    @api.onchange('product_id')
    def _onchange_product(self):
        uom = False
        price = 0.00
        for line in self:
            for prod in line.product_id:
                uom = prod.uom_id.id
                price = prod.list_price
            line.write({'uom_id': uom,
                        'cur_unit_price': price,
                        'adj_unit_price': price,
                        })

    @api.onchange('adj_qty')
    def _onchange_adjusted_qty(self):
        for line in self:
            check_qty = line.adj_qty + line.cur_qty
            if line.itb_id.is_change_allocation == True:
                if check_qty < 0:
                    raise ValidationError(_("The adjusted quantity is less than current quantity."))
                elif line.adj_qty > line.unallocated_qty:
                    if not line.is_newly_added_product and line.bd_material_id:
                        raise ValidationError(_("The adjusted quantity is over the unallocated quantity."))

    @api.onchange('adj_unit_price')
    def _check_product_in_purchase(self):
        for line in self:
            if line.itb_id.is_change_allocation == False:
                if line.cur_qty < line.cs_material_id.budgeted_qty_left:
                    raise ValidationError(
                        _("This product already in purchase operation, you can't change the unit price."))
                else:
                    pass

    def delete_itb_material_line_ids(self):
        for line in self:
            line.write({'adj_qty': line.cur_qty * -1,
                        'is_delete': True
                        })
            line.itb_id._get_line_change()


class ITBLabourLine(models.Model):
    _name = 'internal.transfer.budget.labour.line'
    _description = 'Internal Transfer Budget Labour Line'
    _order = 'id,sequence'

    itb_id = fields.Many2one('internal.transfer.budget', string="Internal Transfer Budget", ondelete='cascade')
    job_sheet_id = fields.Many2one(related='itb_id.job_sheet_id', string="Cost Sheet")
    project_budget = fields.Many2one(related='itb_id.project_budget', string='Periodical Budget')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    cs_labour_id = fields.Many2one('material.labour', 'CS Labour ID', compute='_get_cs_id')
    bd_labour_id = fields.Many2one('budget.labour', 'BD labour ID', compute='_get_bd_id')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    cur_qty = fields.Float('Current Quantity', default=0.00)
    cur_contractors = fields.Float('Current Contractors', default=0.00)
    cur_time = fields.Float('Current Time', default=0.00)
    adj_qty = fields.Float('Quantity', default=0.00)
    adj_contractors = fields.Float('Contractors', default=0.00)
    adj_time = fields.Float('Time', default=0.00)
    unallocated_time = fields.Float(related='cs_labour_id.unallocated_budget_time')
    unallocated_contractors = fields.Integer(related='cs_labour_id.unallocated_contractors')
    unallocated_qty = fields.Float(related='cs_labour_id.product_qty_na')
    unallocated_amt = fields.Float(related='cs_labour_id.product_amt_na')
    cal_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_qty")
    cal_time = fields.Float('Calculated Time', default=0.00, compute="_compute_cal_time")
    cal_contractors = fields.Float('Calculated Contractors', default=0.00, compute="_compute_cal_contractors")
    cal_cs_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_cs_qty")
    cal_cs_time = fields.Float('Calculated CS Time', default=0.00, compute="_compute_cal_cs_time")
    cal_cs_contractors = fields.Float('Calculated CS Contractors', default=0.00, compute="_compute_cal_cs_contractors")
    cur_unit_price = fields.Float('Current Unit price', default=0.00)
    adj_unit_price = fields.Float('Adjusted Unit price', default=0.00)
    cur_amt = fields.Float('Current Amount', default=0.00)
    adj_amt = fields.Float('Amount', default=0.00, compute="_compute_adjusted")
    adjusted = fields.Float('Adjusted', default=0.00, compute="_compute_adjusted")
    is_delete = fields.Boolean(string='Deleted', default=False)
    project_id = fields.Many2one(related='itb_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    is_newly_added_product = fields.Boolean('Is newly added product', compute="_compute_is_newly_added_product",
                                            store=True)
    is_change_allocation = fields.Boolean(related='itb_id.is_change_allocation', string='Is Change Allocation')
    is_generated = fields.Boolean('is generated')
    is_not_from_cost_sheet = fields.Boolean('Is not from cost sheet', compute='_compute_is_not_from_cost_sheet',
                                            store=True)
    adj_unallocated_time = fields.Float('Adjusted Unallocated Time', default=0.00,
                                        compute="_compute_adjusted_unallocated_time")
    adj_unallocated_contractors = fields.Integer('Adjusted Unallocated Contractors', default=0.00,
                                                 compute="_compute_adjusted_unallocated_contractors")
    adj_unallocated_qty = fields.Float('Adjusted Unallocated Quantity', default=0.00,
                                       compute="_compute_adjusted_unallocated_qty")
    adj_unallocated_amt = fields.Float('Adjusted Unallocated Amount', default=0.00,
                                       compute="_compute_adjusted_unallocated_amt")

    @api.depends('adj_qty', 'unallocated_qty')
    def _compute_adjusted_unallocated_qty(self):
        for rec in self:
            rec.adj_unallocated_qty = rec.unallocated_qty + (rec.adj_qty * -1)

    @api.depends('adj_contractors', 'unallocated_contractors')
    def _compute_adjusted_unallocated_contractors(self):
        for rec in self:
            rec.adj_unallocated_contractors = rec.unallocated_contractors + (rec.adj_contractors * -1)

    @api.depends('adj_time', 'unallocated_time')
    def _compute_adjusted_unallocated_time(self):
        for rec in self:
            rec.adj_unallocated_time = rec.unallocated_time + (rec.adj_time * -1)

    @api.depends('adj_qty', 'unallocated_amt')
    def _compute_adjusted_unallocated_amt(self):
        for rec in self:
            rec.adj_unallocated_amt = rec.adj_unallocated_qty * rec.cur_unit_price

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _compute_is_newly_added_product(self):
        for rec in self:
            is_newly_added_product = False
            line_required_data = [rec.project_scope.id, rec.section_name.id, rec.group_of_product.id, rec.product_id.id]

            if rec.project_budget and not rec.is_generated and False not in line_required_data:
                budget_change = rec.project_scope.name + rec.section_name.name + rec.group_of_product.name + \
                                rec.product_id.name
                periodical_budget = [
                    i.project_scope.name + i.section_name.name + i.group_of_product.name + i.product_id.name for i
                    in rec.project_budget.budget_labour_ids]

                if budget_change not in periodical_budget:
                    is_newly_added_product = True
            rec.is_newly_added_product = is_newly_added_product

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _get_cs_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product and res.product_id:
                # line = self.env['material.labour'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id),
                #      ('product_id', '=', res.product_id.id)], limit=1)
                line = res.itb_id.job_sheet_id.material_labour_ids.filtered(
                    lambda x: x.project_scope == res.project_scope and
                              x.section_name == res.section_name and
                              x.group_of_product == res.group_of_product
                              and x.product_id == res.product_id)
                if line:
                    res.cs_labour_id = line.id
                else:
                    res.cs_labour_id = False
            else:
                res.cs_labour_id = False

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _get_bd_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product and res.product_id:
                # line = self.env['budget.labour'].search(
                #     [('budget_id', '=', res.project_budget.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id),
                #      ('product_id', '=', res.product_id.id)], limit=1)
                line = res.project_budget.budget_labour_ids.filtered(lambda x: x.project_scope == res.project_scope and
                                                                               x.section_name == res.section_name and
                                                                               x.group_of_product == res.group_of_product
                                                                               and x.product_id == res.product_id)
                if line:
                    res.bd_labour_id = line.id
                else:
                    res.bd_labour_id = False
            else:
                res.bd_labour_id = False

    @api.depends('product_id')
    def _compute_is_not_from_cost_sheet(self):
        for rec in self:
            is_not_from_cost_sheet = False
            if not rec.cs_labour_id:
                is_not_from_cost_sheet = True
            rec.is_not_from_cost_sheet = is_not_from_cost_sheet

    #@api.onchange('product_id')
    #def line_validation(self):
    #    for rec in self:
    #        if rec.product_id:
    #            if not rec.cs_labour_id:
    #                rec._get_cs_id()
    #                if rec.project_budget.budgeting_method == 'product_budget' and not rec.cs_labour_id:
    #                    raise ValidationError(_("You're not allowed to add new product that is not from "
    #                                            "cost sheet in this budgeting method."))
    #                elif (rec.project_budget.budgeting_method == 'product_budget' and not rec.bd_labour_id
    #                      and rec.is_newly_added_product and rec.is_change_allocation):
    #                    if rec.unallocated_qty == 0:
    #                        raise ValidationError(_("You're not allowed to add new product that is already "
    #                                                "allocated all its unallocated quantity to Periodical Budget."))
    #                elif rec.project_budget.budgeting_method == 'gop_budget':
    #                    if rec.group_of_product not in rec.project_budget.budget_labour_ids.mapped(
    #                            'group_of_product'):
    #                        raise ValidationError(_("You're not allowed to add new group of product that is not "
    #                                                "from cost sheet in this budgeting method."))

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.adj_time = 1.0
            self.adj_contractors = 1.0
            self.adj_unit_price = self.cs_labour_id.price_unit
            self.description = self.product_id.display_name
        else:
            self.uom_id = False
            self.adj_qty = False
            self.adj_unit_price = False
            self.description = False

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                for line in rec.itb_id.itb_section_ids:
                    if rec.project_scope._origin.id == line.project_scope_id._origin.id:
                        section.append(line.section_id._origin.id)
            rec.project_section_computed = [(6, 0, section)]

    @api.onchange('section_name')
    def _onchange_section_name(self):
        for rec in self:
            if rec.is_change_allocation:
                group_of_product = []
                if rec.section_name and rec.job_sheet_id:
                    for labour in rec.job_sheet_id.material_labour_ids:
                        if (labour.group_of_product.id not in group_of_product and
                                labour.section_name.id == rec.section_name.id):
                            group_of_product.append(labour.group_of_product.id)
                return {
                    'domain': {'group_of_product': [('id', 'in', group_of_product)]}
                }

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product)]}
            }

    @api.depends('itb_id.itb_labour_line_ids', 'itb_id.itb_labour_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.itb_id.itb_labour_line_ids:
                no += 1
                l.sr_no = no

    def _compute_cal_qty(self):
        for line in self:
            line.cal_qty = line.cur_qty + line.adj_qty

    def _compute_cal_time(self):
        for line in self:
            line.cal_time = line.cur_time + line.adj_time

    def _compute_cal_contractors(self):
        for line in self:
            line.cal_contractors = line.cur_contractors + line.adj_contractors

    def _compute_cal_cs_qty(self):
        for line in self:
            if line.bd_labour_id:
                line.cal_cs_qty = line.bd_labour_id.quantity + line.adj_qty
            else:
                line.cal_cs_qty = line.cs_labour_id.product_qty + line.adj_qty

    def _compute_cal_cs_time(self):
        for line in self:
            if line.bd_labour_id:
                line.cal_cs_time = line.bd_labour_id.time_left + line.adj_time
            else:
                line.cal_cs_time = line.cs_labour_id.time_left + line.adj_time

    def _compute_cal_cs_contractors(self):
        for line in self:
            if line.bd_labour_id:
                line.cal_cs_contractors = line.bd_labour_id.contractors + line.adj_contractors
            else:
                line.cal_cs_contractors = line.cs_labour_id.contractors + line.adj_contractors

    @api.depends('adj_unit_price', 'adj_time', 'adj_contractors')
    def _compute_adjusted(self):
        qty = 0.00
        amt = 0.00
        adj = 0.00
        for line in self:
            check_time = line.adj_time + line.cur_time
            check_contractors = line.adj_contractors + line.cur_contractors

            if check_contractors < 0:
                raise ValidationError(_("The adjusted contractors is over the remaining time."))
            if check_time < 0:
                raise ValidationError(_("The adjusted time is over the remaining time."))
            elif line.adj_unit_price < 0:
                raise ValidationError(_("Adjusted amount cannot set below the current amount."))
            else:
                if line.adj_unit_price != line.cur_unit_price and line.adj_time != 0 and line.adj_contractors != 0:
                    time = line.adj_time + line.cur_time
                    contractors = line.adj_contractors + line.cur_contractors
                    amt = time * line.adj_unit_price * contractors
                elif line.adj_unit_price != line.cur_unit_price and line.adj_time != 0 and line.adj_contractors == 0:
                    time = line.adj_time + line.cur_time
                    contractors = line.cur_contractors
                    amt = time * line.adj_unit_price * contractors
                elif line.adj_unit_price != line.cur_unit_price and line.adj_time == 0 and line.adj_contractors != 0:
                    time = line.cur_time
                    contractors = line.adj_contractors + line.cur_contractors
                    amt = time * line.adj_unit_price * contractors
                elif line.adj_unit_price != line.cur_unit_price and (line.adj_time == 0 and line.adj_contractors == 0):
                    time = line.cur_time
                    contractors = line.cur_contractors
                    amt = time * line.adj_unit_price * contractors
                elif (line.adj_time != 0 or line.adj_contractors != 0) and line.adj_unit_price == line.cur_unit_price:
                    time = line.adj_time + line.cur_time
                    contractors = line.adj_contractors + line.cur_contractors
                    amt = time * line.cur_unit_price * contractors
                else:
                    # time = line.cur_time
                    amt = line.cur_amt
                # adj = amt - line.cur_amt

                if line.adj_unit_price != line.cur_unit_price:
                    if line.adj_time == 0 and line.cur_time == 0:
                        raise ValidationError(
                            _("You can't change the unit price if budget amount left is the return amount of your transaction."
                              "Please consider to use 'Claim Budget Left' on Cost Sheet or Periodical Budget in line's corresponding estimation tab."))

                adj = ((line.cur_contractors + line.adj_contractors) * (
                            line.cur_time + line.adj_time) * line.adj_unit_price) - (
                                  (line.cur_contractors * line.cur_time) * line.cur_unit_price)
                line.write({'adj_amt': amt,
                            'adjusted': adj,
                            'cal_time': check_time,
                            })

    @api.onchange('adj_time', 'adj_contractors')
    def _onchange_adjusted_qty(self):
        for line in self:
            check_time = line.adj_time + line.cur_time
            check_contractors = line.adj_contractors + line.cur_contractors

            if line.itb_id.is_change_allocation == True:
                if check_time < 0:
                    raise ValidationError(_("The adjusted time is less than current time."))
                elif line.adj_time > line.unallocated_time:
                    if not line.is_newly_added_product and line.bd_labour_id:
                        raise ValidationError(_("The adjusted time is over the unallocated time."))
                if check_contractors < 0:
                    raise ValidationError(_("The adjusted contractors is less than current contractors."))
                elif line.adj_contractors > line.unallocated_contractors:
                    if not line.is_newly_added_product and line.bd_labour_id:
                        raise ValidationError(_("The adjusted contractors is over the unallocated contractors."))

    @api.onchange('adj_unit_price')
    def _check_product_in_purchase(self):
        for line in self:
            if line.itb_id.is_change_allocation == False:
                if line.cur_qty < line.cs_labour_id.budgeted_qty_left:
                    raise ValidationError(
                        _("This product already in purchase operation, you can't change the unit price."))
                else:
                    pass

    def delete_itb_labour_line_ids(self):
        for line in self:
            line.write({'adj_qty': line.cur_qty * -1,
                        'is_delete': True
                        })
            line.itb_id._get_line_change()


class ITBOverheadLine(models.Model):
    _name = 'internal.transfer.budget.overhead.line'
    _description = 'Internal Transfer Budget Overhead Line'
    _order = 'id,sequence'

    itb_id = fields.Many2one('internal.transfer.budget', string="Internal Transfer Budget", ondelete='cascade')
    job_sheet_id = fields.Many2one(related='itb_id.job_sheet_id', string="Cost Sheet")
    project_budget = fields.Many2one(related='itb_id.project_budget', string='Periodical Budget')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    cs_overhead_id = fields.Many2one('material.overhead', 'CS Overhead ID', compute="_get_cs_id")
    bd_overhead_id = fields.Many2one('budget.overhead', 'BD Overhead ID', compute="_get_bd_id")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    overhead_catagory = fields.Selection([
        ('product', 'Product'),
        ('petty cash', 'Petty Cash'),
        ('cash advance', 'Cash Advance'),
        ('fuel', 'Fuel'),
    ], string='Overhead Catagory')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    cur_qty = fields.Float('Current Quantity', default=0.00)
    adj_qty = fields.Float('Quantity', default=0.00)
    unallocated_qty = fields.Float(related='cs_overhead_id.product_qty_na')
    unallocated_amt = fields.Float(related='cs_overhead_id.product_amt_na')
    cal_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_qty")
    cal_cs_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_cs_qty")
    cur_unit_price = fields.Float('Current Unit price', default=0.00)
    adj_unit_price = fields.Float('Adjusted Unit price', default=0.00)
    cur_amt = fields.Float('Current Amount', default=0.00)
    adj_amt = fields.Float('Amount', default=0.00, compute="_compute_adjusted")
    adjusted = fields.Float('Adjusted', default=0.00, compute="_compute_adjusted")
    is_delete = fields.Boolean(string='Deleted', default=False)
    project_id = fields.Many2one(related='itb_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    is_newly_added_product = fields.Boolean('Is newly added product', compute="_compute_is_newly_added_product",
                                            store=True)
    is_change_allocation = fields.Boolean(related='itb_id.is_change_allocation', string='Is Change Allocation')
    is_generated = fields.Boolean('is generated')
    is_not_from_cost_sheet = fields.Boolean('Is not from cost sheet', compute='_compute_is_not_from_cost_sheet',
                                            store=True)
    adj_unallocated_qty = fields.Float('Adjusted Unallocated Quantity', default=0.00,
                                       compute="_compute_adjusted_unallocated_qty")
    adj_unallocated_amt = fields.Float('Adjusted Unallocated Amount', default=0.00,
                                       compute="_compute_adjusted_unallocated_amt")

    @api.depends('adj_qty', 'unallocated_qty')
    def _compute_adjusted_unallocated_qty(self):
        for rec in self:
            rec.adj_unallocated_qty = rec.unallocated_qty + (rec.adj_qty * -1)

    @api.depends('adj_qty', 'unallocated_amt')
    def _compute_adjusted_unallocated_amt(self):
        for rec in self:
            rec.adj_unallocated_amt = rec.adj_unallocated_qty * rec.cur_unit_price

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _compute_is_newly_added_product(self):
        for rec in self:
            is_newly_added_product = False
            line_required_data = [rec.project_scope.id, rec.section_name.id, rec.group_of_product.id, rec.product_id.id]

            if rec.project_budget and not rec.is_generated and False not in line_required_data:
                budget_change = rec.project_scope.name + rec.section_name.name + rec.group_of_product.name + \
                                rec.product_id.name
                periodical_budget = [
                    i.project_scope.name + i.section_name.name + i.group_of_product.name + i.product_id.name for i
                    in rec.project_budget.budget_overhead_ids]

                if budget_change not in periodical_budget:
                    is_newly_added_product = True
            rec.is_newly_added_product = is_newly_added_product

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _get_cs_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product and res.product_id:
                # line = self.env['material.overhead'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id),
                #      ('product_id', '=', res.product_id.id)], limit=1)
                line = res.itb_id.job_sheet_id.material_overhead_ids.filtered(
                    lambda x: x.project_scope == res.project_scope and
                              x.section_name == res.section_name and
                              x.group_of_product == res.group_of_product
                              and x.product_id == res.product_id)
                if line:
                    res.cs_overhead_id = line.id
                else:
                    res.cs_overhead_id = False
            else:
                res.cs_overhead_id = False

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _get_bd_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product and res.product_id:
                # line = self.env['budget.overhead'].search(
                #     [('budget_id', '=', res.project_budget.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id),
                #      ('product_id', '=', res.product_id.id)], limit=1)
                line = res.project_budget.budget_overhead_ids.filtered(
                    lambda x: x.project_scope == res.project_scope and
                              x.section_name == res.section_name and
                              x.group_of_product == res.group_of_product
                              and x.product_id == res.product_id)
                if line:
                    res.bd_overhead_id = line.id
                else:
                    res.bd_overhead_id = False
            else:
                res.bd_overhead_id = False

    @api.depends('product_id')
    def _compute_is_not_from_cost_sheet(self):
        for rec in self:
            is_not_from_cost_sheet = False
            if not rec.cs_overhead_id:
                is_not_from_cost_sheet = True
            rec.is_not_from_cost_sheet = is_not_from_cost_sheet

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.adj_qty = 1.0
            self.adj_unit_price = self.cs_overhead_id.price_unit
            self.description = self.product_id.display_name
        else:
            self.uom_id = False
            self.adj_qty = False
            self.adj_unit_price = False
            self.description = False

    #@api.onchange('product_id')
    #def line_validation(self):
    #    for rec in self:
    #        if rec.product_id:
    #            if not rec.cs_overhead_id:
    #                rec._get_cs_id()
    #                if rec.project_budget.budgeting_method == 'product_budget' and not rec.cs_overhead_id:
    #                    raise ValidationError(_("You're not allowed to add new product that is not from "
    #                                            "cost sheet in this budgeting method."))
    #                elif (rec.project_budget.budgeting_method == 'product_budget' and not rec.bd_overhead_id
    #                      and rec.is_newly_added_product and rec.is_change_allocation):
    #                    if rec.unallocated_qty == 0:
    #                        raise ValidationError(_("You're not allowed to add new product that is already "
    #                                                "allocated all its unallocated quantity to Periodical Budget."))
    #                elif rec.project_budget.budgeting_method == 'gop_budget':
    #                    if rec.group_of_product not in rec.project_budget.budget_overhead_ids.mapped(
    #                            'group_of_product'):
    #                        raise ValidationError(_("You're not allowed to add new group of product that is not "
    #                                                "from cost sheet in this budgeting method."))

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                for line in rec.itb_id.itb_section_ids:
                    if rec.project_scope._origin.id == line.project_scope_id._origin.id:
                        section.append(line.section_id._origin.id)
            rec.project_section_computed = [(6, 0, section)]

    @api.onchange('section_name')
    def _onchange_section_name(self):
        for rec in self:
            if rec.is_change_allocation:
                group_of_product = []
                if rec.section_name and rec.job_sheet_id:
                    for overhead in rec.job_sheet_id.material_overhead_ids:
                        if (overhead.group_of_product.id not in group_of_product and
                                overhead.section_name.id == rec.section_name.id):
                            group_of_product.append(overhead.group_of_product.id)
                return {
                    'domain': {'group_of_product': [('id', 'in', group_of_product)]}
                }

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product)]}
            }

    @api.depends('itb_id.itb_overhead_line_ids', 'itb_id.itb_overhead_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.itb_id.itb_overhead_line_ids:
                no += 1
                l.sr_no = no

    def _compute_cal_qty(self):
        for line in self:
            line.cal_qty = line.cur_qty + line.adj_qty

    def _compute_cal_cs_qty(self):
        for line in self:
            if line.bd_overhead_id:
                line.cal_cs_qty = line.bd_overhead_id.quantity + line.adj_qty
            else:
                line.cal_cs_qty = line.cs_overhead_id.product_qty + line.adj_qty

    @api.depends('adj_unit_price', 'adj_qty')
    def _compute_adjusted(self):
        qty = 0.00
        amt = 0.00
        adj = 0.00
        for line in self:
            check_qty = line.adj_qty + line.cur_qty

            if check_qty < 0:
                raise ValidationError(_("The adjusted quantity is over the remaining quantity."))
            elif line.adj_unit_price < 0:
                raise ValidationError(_("Adjusted amount cannot set below the current amount."))
            else:
                if line.adj_unit_price != line.cur_unit_price and line.adj_qty != 0:
                    qty = line.adj_qty + line.cur_qty
                    amt = qty * line.adj_unit_price
                elif line.adj_unit_price != line.cur_unit_price and line.adj_qty == 0:
                    qty = line.cur_qty
                    amt = line.cur_qty * line.adj_unit_price
                elif line.adj_qty != 0 and line.adj_unit_price == line.cur_unit_price:
                    qty = line.adj_qty + line.cur_qty
                    amt = qty * line.cur_unit_price
                else:
                    qty = line.cur_qty
                    amt = line.cur_amt
                # adj = amt - line.cur_amt

                if line.adj_unit_price != line.cur_unit_price:
                    if line.adj_qty == 0 and line.cur_qty == 0:
                        raise ValidationError(
                            _("You can't change the unit price if budget amount left is the return amount of your transaction."
                              "Please consider to use 'Claim Budget Left' on Cost Sheet or Periodical Budget in line's corresponding estimation tab."))
                    else:
                        adj = (line.cur_amt - (line.adj_qty + line.cur_qty) * line.adj_unit_price) * -1
                else:
                    adj = line.adj_qty * line.adj_unit_price
                line.write({'adj_amt': amt,
                            'adjusted': adj,
                            'cal_qty': check_qty,
                            })

    @api.onchange('adj_qty')
    def _onchange_adjusted_qty(self):
        for line in self:
            check_qty = line.adj_qty + line.cur_qty
            if line.itb_id.is_change_allocation == True:
                if check_qty < 0:
                    raise ValidationError(_("The adjusted quantity is less than current quantity."))
                elif line.adj_qty > line.unallocated_qty:
                    if not line.is_newly_added_product and line.bd_overhead_id:
                        raise ValidationError(_("The adjusted quantity is over the unallocated quantity."))

    @api.onchange('adj_unit_price')
    def _check_product_in_purchase(self):
        for line in self:
            if line.itb_id.is_change_allocation == False:
                if line.cur_qty < line.cs_overhead_id.budgeted_qty_left:
                    raise ValidationError(
                        _("This product already in purchase operation, you can't change the unit price."))
                else:
                    pass

    def delete_itb_overhead_line_ids(self):
        for line in self:
            line.write({'adj_qty': line.cur_qty * -1,
                        'is_delete': True
                        })
            line.itb_id._get_line_change()


class ITBInternalAssetLine(models.Model):
    _name = 'internal.transfer.budget.internal.asset.line'
    _description = 'Internal Transfer Budget Internal Asset Line'
    _order = 'id,sequence'

    itb_id = fields.Many2one('internal.transfer.budget', string="Internal Transfer Budget", ondelete='cascade')
    job_sheet_id = fields.Many2one(related='itb_id.job_sheet_id', string="Cost Sheet")
    project_budget = fields.Many2one(related='itb_id.project_budget', string='Periodical Budget')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    cs_asset_id = fields.Many2one('internal.asset', 'CS Asset ID', compute="_get_cs_id")
    bd_asset_id = fields.Many2one('budget.internal.asset', 'BD Asset ID', compute="_get_bd_id")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    cur_qty = fields.Float('Current Quantity', default=0.00)
    adj_qty = fields.Float('Quantity', default=0.00)
    unallocated_qty = fields.Float(related='cs_asset_id.unallocated_budget_qty')
    unallocated_amt = fields.Float(related='cs_asset_id.unallocated_amt')
    cal_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_qty")
    cal_cs_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_cs_qty")
    cur_unit_price = fields.Float('Current Unit price', default=0.00)
    adj_unit_price = fields.Float('Adjusted Unit price', default=0.00)
    cur_amt = fields.Float('Current Amount', default=0.00)
    adj_amt = fields.Float('Amount', default=0.00, compute="_compute_adjusted")
    adjusted = fields.Float('Adjusted', default=0.00, compute="_compute_adjusted")
    is_delete = fields.Boolean(string='Deleted', default=False)
    project_id = fields.Many2one(related='itb_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    is_newly_added_product = fields.Boolean('Is newly added product', compute="_compute_is_newly_added_product",
                                            store=True)
    is_change_allocation = fields.Boolean(related='itb_id.is_change_allocation', string='Is Change Allocation')
    is_generated = fields.Boolean('is generated')
    is_not_from_cost_sheet = fields.Boolean('Is not from cost sheet', compute='_compute_is_not_from_cost_sheet',
                                            store=True)
    adj_unallocated_qty = fields.Float('Adjusted Unallocated Quantity', default=0.00,
                                       compute="_compute_adjusted_unallocated_qty")
    adj_unallocated_amt = fields.Float('Adjusted Unallocated Amount', default=0.00,
                                       compute="_compute_adjusted_unallocated_amt")

    @api.depends('adj_qty', 'unallocated_qty')
    def _compute_adjusted_unallocated_qty(self):
        for rec in self:
            rec.adj_unallocated_qty = rec.unallocated_qty + (rec.adj_qty * -1)

    @api.depends('adj_qty', 'unallocated_amt')
    def _compute_adjusted_unallocated_amt(self):
        for rec in self:
            rec.adj_unallocated_amt = rec.adj_unallocated_qty * rec.cur_unit_price

    @api.depends('project_scope', 'section_name', 'asset_category_id', 'asset_id')
    def _compute_is_newly_added_product(self):
        for rec in self:
            is_newly_added_product = False
            line_required_data = [rec.project_scope.id, rec.section_name.id, rec.asset_category_id.id, rec.asset_id.id]

            if rec.project_budget and not rec.is_generated and False not in line_required_data:
                budget_change = rec.project_scope.name + rec.section_name.name + rec.asset_category_id.name + \
                                rec.asset_id.name
                periodical_budget = [
                    i.project_scope.name + i.section_name.name + i.group_of_product.name + i.product_id.name for i
                    in rec.project_budget.budget_equipment_ids]

                if budget_change not in periodical_budget:
                    is_newly_added_product = True
            rec.is_newly_added_product = is_newly_added_product

    @api.depends('project_scope', 'section_name', 'asset_category_id', 'asset_id')
    def _get_cs_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.asset_category_id and res.asset_id:
                # line = self.env['internal.asset'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('asset_category_id', '=', res.asset_category_id.id),
                #      ('asset_id', '=', res.asset_id.id)], limit=1)
                line = res.itb_id.job_sheet_id.internal_asset_ids.filtered(
                    lambda x: x.project_scope == res.project_scope and
                              x.section_name == res.section_name and
                              x.asset_category_id == res.asset_category_id
                              and x.asset_id == res.asset_id)
                if line:
                    res.cs_asset_id = line.id
                else:
                    res.cs_asset_id = False
            else:
                res.cs_asset_id = False

    @api.depends('project_scope', 'section_name', 'asset_category_id', 'asset_id')
    def _get_bd_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.asset_category_id and res.asset_id:
                # line = self.env['budget.internal.asset'].search(
                #     [('project_budget_id', '=', res.project_budget.id),
                #      ('project_scope_line_id', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('asset_category_id', '=', res.asset_category_id.id),
                #      ('asset_id', '=', res.asset_id.id)], limit=1)
                line = res.project_budget.budget_internal_asset_ids.filtered(lambda
                                                                                 x: x.project_scope_line_id == res.project_scope and x.section_name == res.section_name and x.asset_category_id == res.asset_category_id and x.asset_id == res.asset_id)
                if line:
                    res.bd_asset_id = line.id
                else:
                    res.bd_asset_id = False
            else:
                res.bd_asset_id = False

    @api.depends('asset_id')
    def _compute_is_not_from_cost_sheet(self):
        for rec in self:
            is_not_from_cost_sheet = False
            if not rec.cs_asset_id:
                is_not_from_cost_sheet = True
            rec.is_not_from_cost_sheet = is_not_from_cost_sheet

    #@api.onchange('asset_id')
    #def line_validation(self):
    #    for rec in self:
    #        if rec.asset_id:
    #            if not rec.cs_asset_id:
    #                rec._get_cs_id()
    #                if rec.project_budget.budgeting_method == 'product_budget' and not rec.cs_asset_id:
    #                    raise ValidationError(_("You're not allowed to add new product that is not from "
    #                                            "cost sheet in this budgeting method."))
    #                elif (rec.project_budget.budgeting_method == 'product_budget' and not rec.bd_asset_id
    #                      and rec.is_newly_added_product and rec.is_change_allocation):
    #                    if rec.unallocated_qty == 0:
    #                        raise ValidationError(_("You're not allowed to add new product that is already "
    #                                                "allocated all its unallocated quantity to Periodical Budget."))
    #                elif rec.project_budget.budgeting_method == 'gop_budget':
    #                    if rec.asset_category_id not in rec.project_budget.budget_equipment_ids.mapped(
    #                            'group_of_product'):
    #                        raise ValidationError(_("You're not allowed to add new group of product that is not "
    #                                                "from cost sheet in this budgeting method."))

    @api.onchange('asset_id')
    def onchange_asset_id(self):
        if self.asset_id:
            self.uom_id = self.cs_asset_id.uom_id.id
            self.adj_qty = 1.0
            self.adj_unit_price = self.cs_asset_id.price_unit
            self.description = self.asset_id.display_name
        else:
            self.uom_id = False
            self.adj_qty = False
            self.adj_unit_price = False
            self.description = False

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                for line in rec.itb_id.itb_section_ids:
                    if rec.project_scope._origin.id == line.project_scope_id._origin.id:
                        section.append(line.section_id._origin.id)
            rec.project_section_computed = [(6, 0, section)]

    @api.onchange('section_name')
    def _onchange_section_name(self):
        for rec in self:
            if rec.is_change_allocation:
                asset_category = []
                if rec.section_name and rec.job_sheet_id:
                    for asset in rec.job_sheet_id.internal_asset_ids:
                        if (asset.asset_category_id.id not in asset_category and
                                asset.section_name.id == rec.section_name.id):
                            asset_category.append(asset.asset_category_id.id)
                return {
                    'domain': {'group_of_product': [('id', 'in', asset_category)]}
                }

    @api.onchange('asset_category_id')
    def _onchange_asset_category_id(self):
        for rec in self:
            asset_category_id = rec.asset_category_id.id if rec.asset_category_id else False
            return {
                'domain': {'asset_id': [('category_id', '=', asset_category_id)]}
            }

    @api.depends('itb_id.itb_internal_asset_line_ids', 'itb_id.itb_internal_asset_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.itb_id.itb_internal_asset_line_ids:
                no += 1
                l.sr_no = no

    def _compute_cal_qty(self):
        for line in self:
            line.cal_qty = line.cur_qty + line.adj_qty

    def _compute_cal_cs_qty(self):
        for line in self:
            if line.bd_asset_id:
                line.cal_cs_qty = line.bd_asset_id.budgeted_qty + line.adj_qty
            else:
                line.cal_cs_qty = line.cs_asset_id.budgeted_qty + line.adj_qty

    @api.depends('adj_unit_price', 'adj_qty')
    def _compute_adjusted(self):
        qty = 0.00
        amt = 0.00
        adj = 0.00
        for line in self:
            check_qty = line.adj_qty + line.cur_qty

            if check_qty < 0:
                raise ValidationError(_("The adjusted quantity is over the remaining quantity."))
            elif line.adj_unit_price < 0:
                raise ValidationError(_("Adjusted amount cannot set below the current amount."))
            else:
                if line.adj_unit_price != line.cur_unit_price and line.adj_qty != 0:
                    qty = line.adj_qty + line.cur_qty
                    amt = qty * line.adj_unit_price
                elif line.adj_unit_price != line.cur_unit_price and line.adj_qty == 0:
                    qty = line.cur_qty
                    amt = line.cur_qty * line.adj_unit_price
                elif line.adj_qty != 0 and line.adj_unit_price == line.cur_unit_price:
                    qty = line.adj_qty + line.cur_qty
                    amt = qty * line.cur_unit_price
                else:
                    qty = line.cur_qty
                    amt = line.cur_amt
                # adj = amt - line.cur_amt
                if line.adj_unit_price != line.cur_unit_price:
                    if line.adj_qty == 0 and line.cur_qty == 0:
                        raise ValidationError(
                            _("You can't change the unit price if budget amount left is the return amount of your transaction."
                              "Please consider to use 'Claim Budget Left' on Cost Sheet or Periodical Budget in line's corresponding estimation tab."))
                    else:
                        adj = (line.cur_amt - (line.adj_qty + line.cur_qty) * line.adj_unit_price) * -1
                else:
                    adj = line.adj_qty * line.adj_unit_price
                line.write({'adj_amt': amt,
                            'adjusted': adj,
                            'cal_qty': check_qty,
                            })

    @api.onchange('adj_qty')
    def _onchange_adjusted_qty(self):
        for line in self:
            check_qty = line.adj_qty + line.cur_qty
            if line.itb_id.is_change_allocation == True:
                if check_qty < 0:
                    raise ValidationError(_("The adjusted quantity is less than current quantity."))
                elif line.adj_qty > line.unallocated_qty:
                    if not line.is_newly_added_product and line.bd_asset_id:
                        raise ValidationError(_("The adjusted quantity is over the unallocated quantity."))

    @api.onchange('adj_unit_price')
    def _check_product_in_purchase(self):
        for line in self:
            if line.itb_id.is_change_allocation == False:
                if line.cur_qty < line.cs_asset_id.budgeted_qty_left:
                    raise ValidationError(
                        _("This product already in purchase operation, you can't change the unit price."))
                else:
                    pass

    def delete_itb_equipment_line_ids(self):
        for line in self:
            line.write({'adj_qty': line.cur_qty * -1,
                        'is_delete': True
                        })
            line.itb_id._get_line_change()


class ITBEquipmentLine(models.Model):
    _name = 'internal.transfer.budget.equipment.line'
    _description = 'Internal Transfer Budget Equipment Line'
    _order = 'id,sequence'

    itb_id = fields.Many2one('internal.transfer.budget', string="Internal Transfer Budget", ondelete='cascade')
    job_sheet_id = fields.Many2one(related='itb_id.job_sheet_id', string="Cost Sheet")
    project_budget = fields.Many2one(related='itb_id.project_budget', string='Periodical Budget')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    cs_equipment_id = fields.Many2one('material.equipment', 'CS Equipment ID', compute="_get_cs_id")
    bd_equipment_id = fields.Many2one('budget.equipment', 'BD Equipment ID', compute="_get_bd_id")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    cur_qty = fields.Float('Current Quantity', default=0.00)
    adj_qty = fields.Float('Quantity', default=0.00)
    unallocated_qty = fields.Float(related='cs_equipment_id.product_qty_na')
    unallocated_amt = fields.Float(related='cs_equipment_id.product_amt_na')
    cal_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_qty")
    cal_cs_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_cs_qty")
    cur_unit_price = fields.Float('Current Unit price', default=0.00)
    adj_unit_price = fields.Float('Adjusted Unit price', default=0.00)
    cur_amt = fields.Float('Current Amount', default=0.00)
    adj_amt = fields.Float('Amount', default=0.00, compute="_compute_adjusted")
    adjusted = fields.Float('Adjusted', default=0.00, compute="_compute_adjusted")
    is_delete = fields.Boolean(string='Deleted', default=False)
    project_id = fields.Many2one(related='itb_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    is_newly_added_product = fields.Boolean('Is newly added product', compute="_compute_is_newly_added_product",
                                            store=True)
    is_change_allocation = fields.Boolean(related='itb_id.is_change_allocation', string='Is Change Allocation')
    is_generated = fields.Boolean('is generated')
    is_not_from_cost_sheet = fields.Boolean('Is not from cost sheet', compute='_compute_is_not_from_cost_sheet',
                                            store=True)
    adj_unallocated_qty = fields.Float('Adjusted Unallocated Quantity', default=0.00,
                                       compute="_compute_adjusted_unallocated_qty")
    adj_unallocated_amt = fields.Float('Adjusted Unallocated Amount', default=0.00,
                                       compute="_compute_adjusted_unallocated_amt")

    @api.depends('adj_qty', 'unallocated_qty')
    def _compute_adjusted_unallocated_qty(self):
        for rec in self:
            rec.adj_unallocated_qty = rec.unallocated_qty + (rec.adj_qty * -1)

    @api.depends('adj_qty', 'unallocated_amt')
    def _compute_adjusted_unallocated_amt(self):
        for rec in self:
            rec.adj_unallocated_amt = rec.adj_unallocated_qty * rec.cur_unit_price

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _compute_is_newly_added_product(self):
        for rec in self:
            is_newly_added_product = False
            line_required_data = [rec.project_scope.id, rec.section_name.id, rec.group_of_product.id, rec.product_id.id]

            if rec.project_budget and not rec.is_generated and False not in line_required_data:
                budget_change = rec.project_scope.name + rec.section_name.name + rec.group_of_product.name + \
                                rec.product_id.name
                periodical_budget = [
                    i.project_scope.name + i.section_name.name + i.group_of_product.name + i.product_id.name for i
                    in rec.project_budget.budget_equipment_ids]

                if budget_change not in periodical_budget:
                    is_newly_added_product = True
            rec.is_newly_added_product = is_newly_added_product

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _get_cs_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product and res.product_id:
                # line = self.env['material.equipment'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id),
                #      ('product_id', '=', res.product_id.id)], limit=1)
                line = res.itb_id.job_sheet_id.material_equipment_ids.filtered(
                    lambda x: x.project_scope == res.project_scope and
                              x.section_name == res.section_name and
                              x.group_of_product == res.group_of_product
                              and x.product_id == res.product_id)
                if line:
                    res.cs_equipment_id = line.id
                else:
                    res.cs_equipment_id = False
            else:
                res.cs_equipment_id = False

    @api.depends('project_scope', 'section_name', 'group_of_product', 'product_id')
    def _get_bd_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product and res.product_id:
                # line = self.env['budget.equipment'].search(
                #     [('budget_id', '=', res.project_budget.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id),
                #      ('product_id', '=', res.product_id.id)], limit=1)
                line = res.project_budget.budget_equipment_ids.filtered(
                    lambda x: x.project_scope == res.project_scope and
                              x.section_name == res.section_name and
                              x.group_of_product == res.group_of_product
                              and x.product_id == res.product_id)
                if line:
                    res.bd_equipment_id = line.id
                else:
                    res.bd_equipment_id = False
            else:
                res.bd_equipment_id = False

    @api.depends('product_id')
    def _compute_is_not_from_cost_sheet(self):
        for rec in self:
            is_not_from_cost_sheet = False
            if not rec.cs_equipment_id:
                is_not_from_cost_sheet = True
            rec.is_not_from_cost_sheet = is_not_from_cost_sheet

    #@api.onchange('product_id')
    #def line_validation(self):
    #    for rec in self:
    #        if rec.product_id:
    #            if not rec.cs_equipment_id:
    #                rec._get_cs_id()
    #                if rec.project_budget.budgeting_method == 'product_budget' and not rec.cs_equipment_id:
    #                    raise ValidationError(_("You're not allowed to add new product that is not from "
    #                                            "cost sheet in this budgeting method."))
    #                elif (rec.project_budget.budgeting_method == 'product_budget' and not rec.bd_equipment_id
    #                      and rec.is_newly_added_product and rec.is_change_allocation):
    #                    if rec.unallocated_qty == 0:
    #                        raise ValidationError(_("You're not allowed to add new product that is already "
    #                                                "allocated all its unallocated quantity to Periodical Budget."))
    #                elif rec.project_budget.budgeting_method == 'gop_budget':
    #                    if rec.group_of_product not in rec.project_budget.budget_equipment_ids.mapped(
    #                            'group_of_product'):
    #                        raise ValidationError(_("You're not allowed to add new group of product that is not "
    #                                                "from cost sheet in this budgeting method."))

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.adj_qty = 1.0
            self.adj_unit_price = self.cs_equipment_id.price_unit
            self.description = self.product_id.display_name
        else:
            self.uom_id = False
            self.adj_qty = False
            self.adj_unit_price = False
            self.description = False

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                for line in rec.itb_id.itb_section_ids:
                    if rec.project_scope._origin.id == line.project_scope_id._origin.id:
                        section.append(line.section_id._origin.id)
            rec.project_section_computed = [(6, 0, section)]

    @api.onchange('section_name')
    def _onchange_section_name(self):
        for rec in self:
            if rec.is_change_allocation:
                group_of_product = []
                if rec.section_name and rec.job_sheet_id:
                    for equipment in rec.job_sheet_id.material_equipment_ids:
                        if (equipment.group_of_product.id not in group_of_product and
                                equipment.section_name.id == rec.section_name.id):
                            group_of_product.append(equipment.group_of_product.id)
                return {
                    'domain': {'group_of_product': [('id', 'in', group_of_product)]}
                }

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product)]}
            }

    @api.depends('itb_id.itb_equipment_line_ids', 'itb_id.itb_equipment_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.itb_id.itb_equipment_line_ids:
                no += 1
                l.sr_no = no

    def _compute_cal_qty(self):
        for line in self:
            line.cal_qty = line.cur_qty + line.adj_qty

    def _compute_cal_cs_qty(self):
        for line in self:
            if line.bd_equipment_id:
                line.cal_cs_qty = line.bd_equipment_id.quantity + line.adj_qty
            else:
                line.cal_cs_qty = line.cs_equipment_id.product_qty + line.adj_qty

    @api.depends('adj_unit_price', 'adj_qty')
    def _compute_adjusted(self):
        qty = 0.00
        amt = 0.00
        adj = 0.00
        for line in self:
            check_qty = line.adj_qty + line.cur_qty

            if check_qty < 0:
                raise ValidationError(_("The adjusted quantity is over the remaining quantity."))
            elif line.adj_unit_price < 0:
                raise ValidationError(_("Adjusted amount cannot set below the current amount."))
            else:
                if line.adj_unit_price != line.cur_unit_price and line.adj_qty != 0:
                    qty = line.adj_qty + line.cur_qty
                    amt = qty * line.adj_unit_price
                elif line.adj_unit_price != line.cur_unit_price and line.adj_qty == 0:
                    qty = line.cur_qty
                    amt = line.cur_qty * line.adj_unit_price
                elif line.adj_qty != 0 and line.adj_unit_price == line.cur_unit_price:
                    qty = line.adj_qty + line.cur_qty
                    amt = qty * line.cur_unit_price
                else:
                    qty = line.cur_qty
                    amt = line.cur_amt
                # adj = amt - line.cur_amt
                if line.adj_unit_price != line.cur_unit_price:
                    if line.adj_qty == 0 and line.cur_qty == 0:
                        raise ValidationError(
                            _("You can't change the unit price if budget amount left is the return amount of your transaction."
                              "Please consider to use 'Claim Budget Left' on Cost Sheet or Periodical Budget in line's corresponding estimation tab."))
                    else:
                        adj = (line.cur_amt - (line.adj_qty + line.cur_qty) * line.adj_unit_price) * -1
                else:
                    adj = line.adj_qty * line.adj_unit_price
                line.write({'adj_amt': amt,
                            'adjusted': adj,
                            'cal_qty': check_qty,
                            })

    @api.onchange('adj_qty')
    def _onchange_adjusted_qty(self):
        for line in self:
            check_qty = line.adj_qty + line.cur_qty
            if line.itb_id.is_change_allocation == True:
                if check_qty < 0:
                    raise ValidationError(_("The adjusted quantity is less than current quantity."))
                elif line.adj_qty > line.unallocated_qty:
                    if not line.is_newly_added_product and line.bd_equipment_id:
                        raise ValidationError(_("The adjusted quantity is over the unallocated quantity."))

    @api.onchange('adj_unit_price')
    def _check_product_in_purchase(self):
        for line in self:
            if line.itb_id.is_change_allocation == False:
                if line.cur_qty < line.cs_equipment_id.budgeted_qty_left:
                    raise ValidationError(
                        _("This product already in purchase operation, you can't change the unit price."))
                else:
                    pass

    def delete_itb_equipment_line_ids(self):
        for line in self:
            line.write({'adj_qty': line.cur_qty * -1,
                        'is_delete': True
                        })
            line.itb_id._get_line_change()


class ITBSubconLine(models.Model):
    _name = 'internal.transfer.budget.subcon.line'
    _description = 'Internal Transfer Budget Subcon Line'
    _order = 'id,sequence'

    itb_id = fields.Many2one('internal.transfer.budget', string="Internal Transfer Budget", ondelete='cascade')
    job_sheet_id = fields.Many2one(related='itb_id.job_sheet_id', string="Cost Sheet")
    project_budget = fields.Many2one(related='itb_id.project_budget', string='Periodical Budget')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    cs_subcon_id = fields.Many2one('material.subcon', 'CS Subcon ID', compute="_get_cs_id")
    bd_subcon_id = fields.Many2one('budget.subcon', 'BD subcon ID', compute="_get_bd_id")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    variable = fields.Many2one('variable.template', string='Job Subcon')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    cur_qty = fields.Float('Current Quantity', default=0.00)
    adj_qty = fields.Float('Quantity', default=0.00)
    unallocated_qty = fields.Float(related='cs_subcon_id.product_qty_na')
    unallocated_amt = fields.Float(related='cs_subcon_id.product_amt_na')
    cal_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_qty")
    cal_cs_qty = fields.Float('Calculated Quantity', default=0.00, compute="_compute_cal_cs_qty")
    cur_unit_price = fields.Float('Current Unit price', default=0.00)
    adj_unit_price = fields.Float('Adjusted Unit price', default=0.00)
    cur_amt = fields.Float('Current Amount', default=0.00)
    adj_amt = fields.Float('Amount', default=0.00, compute="_compute_adjusted")
    adjusted = fields.Float('Adjusted', default=0.00, compute="_compute_adjusted")
    is_delete = fields.Boolean(string='Deleted', default=False)
    project_id = fields.Many2one(related='itb_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    is_newly_added_product = fields.Boolean('Is newly added product', compute="_compute_is_newly_added_product",
                                            store=True)
    is_change_allocation = fields.Boolean(related='itb_id.is_change_allocation', string='Is Change Allocation')
    is_generated = fields.Boolean('is generated')
    is_not_from_cost_sheet = fields.Boolean('Is not from cost sheet', compute='_compute_is_not_from_cost_sheet',
                                            store=True)
    adj_unallocated_qty = fields.Float('Adjusted Unallocated Quantity', default=0.00,
                                       compute="_compute_adjusted_unallocated_qty")
    adj_unallocated_amt = fields.Float('Adjusted Unallocated Amount', default=0.00,
                                       compute="_compute_adjusted_unallocated_amt")

    @api.depends('adj_qty', 'unallocated_qty')
    def _compute_adjusted_unallocated_qty(self):
        for rec in self:
            rec.adj_unallocated_qty = rec.unallocated_qty + (rec.adj_qty * -1)

    @api.depends('adj_qty', 'unallocated_amt')
    def _compute_adjusted_unallocated_amt(self):
        for rec in self:
            rec.adj_unallocated_amt = rec.adj_unallocated_qty * rec.cur_unit_price

    @api.depends('project_scope', 'section_name', 'variable')
    def _compute_is_newly_added_product(self):
        for rec in self:
            is_newly_added_product = False
            line_required_data = [rec.project_scope.id, rec.section_name.id, rec.variable.id]

            if rec.project_budget and not rec.is_generated and False not in line_required_data:
                budget_change = rec.project_scope.name + rec.section_name.name + rec.variable.name
                periodical_budget = [
                    i.project_scope.name + i.section_name.name + i.subcon_id.name for i
                    in rec.project_budget.budget_subcon_ids]

                if budget_change not in periodical_budget:
                    is_newly_added_product = True
            rec.is_newly_added_product = is_newly_added_product

    @api.depends('project_scope', 'section_name', 'variable')
    def _get_cs_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.variable:
                # line = self.env['material.subcon'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('variable', '=', res.variable.id)], limit=1)
                line = res.itb_id.job_sheet_id.material_subcon_ids.filtered(
                    lambda x: x.project_scope == res.project_scope and
                              x.section_name == res.section_name and
                              x.variable == res.variable)
                if line:
                    res.cs_subcon_id = line.id
                else:
                    res.cs_subcon_id = False
            else:
                res.cs_subcon_id = False

    @api.depends('project_scope', 'section_name', 'variable')
    def _get_bd_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.variable:
                # line = self.env['budget.subcon'].search(
                #     [('budget_id', '=', res.project_budget.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('subcon_id', '=', res.variable.id)], limit=1)
                line = res.project_budget.budget_subcon_ids.filtered(lambda x: x.project_scope == res.project_scope and
                                                                               x.section_name == res.section_name and
                                                                               x.subcon_id == res.variable)
                if line:
                    res.bd_subcon_id = line.id
                else:
                    res.bd_subcon_id = False
            else:
                res.bd_subcon_id = False

    @api.depends('variable')
    def _compute_is_not_from_cost_sheet(self):
        for rec in self:
            is_not_from_cost_sheet = False
            if not rec.cs_subcon_id:
                is_not_from_cost_sheet = True
            rec.is_not_from_cost_sheet = is_not_from_cost_sheet

    #@api.onchange('variable')
    #def line_validation(self):
    #    for rec in self:
    #        if rec.variable:
    #            if not rec.cs_subcon_id:
    #                rec._get_cs_id()
    #                if rec.project_budget.budgeting_method == 'product_budget' and not rec.cs_subcon_id:
    #                    raise ValidationError(_("You're not allowed to add new product that is not from "
    #                                            "cost sheet in this budgeting method."))
    #                elif (rec.project_budget.budgeting_method == 'product_budget' and not rec.bd_subcon_id
    #                      and rec.is_newly_added_product and rec.is_change_allocation):
    #                    if rec.unallocated_qty == 0:
    #                        raise ValidationError(_("You're not allowed to add new product that is already "
    #                                                "allocated all its unallocated quantity to Periodical Budget."))
    # elif rec.project_budget.budgeting_method == 'gop_budget':
    #     if rec.group_of_product not in rec.project_budget.budget_labour_ids.mapped(
    #             'group_of_product'):
    #         raise ValidationError(_("You're not allowed to add new group of product that is not "
    #                                 "from cost sheet in this budgeting method."))

    @api.onchange('variable')
    def onchange_variable(self):
        if self.variable:
            self.uom_id = self.variable.variable_uom.id
            self.adj_qty = 1.0
            self.adj_unit_price = self.variable.total_variable
            self.description = self.variable.name
        else:
            self.uom_id = False
            self.adj_qty = False
            self.adj_unit_price = False
            self.description = False

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                for line in rec.itb_id.itb_section_ids:
                    if rec.project_scope._origin.id == line.project_scope_id._origin.id:
                        section.append(line.section_id._origin.id)
            rec.project_section_computed = [(6, 0, section)]

    @api.depends('itb_id.itb_subcon_line_ids', 'itb_id.itb_subcon_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.itb_id.itb_subcon_line_ids:
                no += 1
                l.sr_no = no

    def _compute_cal_qty(self):
        for line in self:
            line.cal_qty = line.cur_qty + line.adj_qty

    def _compute_cal_cs_qty(self):
        for line in self:
            if line.bd_subcon_id:
                line.cal_cs_qty = line.bd_subcon_id.quantity + line.adj_qty
            else:
                line.cal_cs_qty = line.cs_subcon_id.product_qty + line.adj_qty

    @api.depends('adj_unit_price', 'adj_qty')
    def _compute_adjusted(self):
        qty = 0.00
        amt = 0.00
        adj = 0.00
        for line in self:
            check_qty = line.adj_qty + line.cur_qty

            if check_qty < 0:
                raise ValidationError(_("The adjusted quantity is over the remaining quantity."))
            elif line.adj_unit_price < 0:
                raise ValidationError(_("Adjusted amount cannot set below the current amount."))
            else:
                if line.adj_unit_price != line.cur_unit_price and line.adj_qty != 0:
                    qty = line.adj_qty + line.cur_qty
                    amt = qty * line.adj_unit_price
                elif line.adj_unit_price != line.cur_unit_price and line.adj_qty == 0:
                    qty = line.cur_qty
                    amt = line.cur_qty * line.adj_unit_price
                elif line.adj_qty != 0 and line.adj_unit_price == line.cur_unit_price:
                    qty = line.adj_qty + line.cur_qty
                    amt = qty * line.cur_unit_price
                else:
                    qty = line.cur_qty
                    amt = line.cur_amt
                # adj = amt - line.cur_amt
                if line.adj_unit_price != line.cur_unit_price:
                    if line.adj_qty == 0 and line.cur_qty == 0:
                        raise ValidationError(_("You can't change the unit price if budget amount left is the return "
                                                "amount of your transaction."
                                                "Please consider to use 'Claim Budget Left' on Cost Sheet or "
                                                "Periodical Budget in line's corresponding estimation tab."))
                    else:
                        adj = (line.cur_amt - (line.adj_qty + line.cur_qty) * line.adj_unit_price) * -1
                else:
                    adj = line.adj_qty * line.adj_unit_price
                line.write({'adj_amt': amt,
                            'adjusted': adj,
                            'cal_qty': check_qty,
                            })

    @api.onchange('adj_qty')
    def _onchange_adjusted_qty(self):
        for line in self:
            check_qty = line.adj_qty + line.cur_qty
            if line.itb_id.is_change_allocation == True:
                if check_qty < 0:
                    raise ValidationError(_("The adjusted quantity is less than current quantity."))
                elif line.adj_qty > line.unallocated_qty:
                    if not line.is_newly_added_product and line.bd_subcon_id:
                        raise ValidationError(_("The adjusted quantity is over the unallocated quantity."))

    @api.onchange('adj_unit_price')
    def _check_product_in_purchase(self):
        for line in self:
            if line.itb_id.is_change_allocation == False:
                if line.cur_qty < line.cs_subcon_id.budgeted_qty_left:
                    raise ValidationError(
                        _("This product already in purchase operation, you can't change the unit price."))
                else:
                    pass

    def delete_itb_subcon_line_ids(self):
        for line in self:
            line.write({'adj_qty': line.cur_qty * -1,
                        'is_delete': True
                        })
            line.itb_id._get_line_change()


class InternalTransferBudgetProjectScope(models.Model):
    _name = "internal.transfer.budget.project.scope"
    _description = "Internal Transfer Budget Project Scope"

    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    project_scope_id = fields.Many2one("project.scope.line", string="Project Scope")
    is_generated = fields.Boolean("Is Generated")
    itb_id = fields.Many2one("internal.transfer.budget", string="Internal Transfer Budget")

    @api.depends('itb_id.itb_project_scope_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.itb_id.itb_project_scope_ids:
                no += 1
                l.sr_no = no


class InternalTransferBudgetSection(models.Model):
    _name = "internal.transfer.budget.section"
    _description = "Internal Transfer Budget Section"

    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    project_scope_id = fields.Many2one("project.scope.line", string="Project Scope")
    section_id = fields.Many2one("section.line", string="Section")
    is_generated = fields.Boolean("Is Generated")
    itb_id = fields.Many2one("internal.transfer.budget", string="Internal Transfer Budget")

    @api.depends('itb_id.itb_section_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.itb_id.itb_section_ids:
                no += 1
                l.sr_no = no


class InternalTransferBudgetApprovalMatrixLine(models.Model):
    _name = 'internal.transfer.budget.approval.matrix.line'
    _description = 'Approval Matrix Table For Budget Change Request'

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
    internal_transfer_budget_id = fields.Many2one('internal.transfer.budget', string='Budget Transfer')
