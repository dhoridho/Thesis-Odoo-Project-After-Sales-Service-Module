from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import ValidationError
from pytz import timezone
from odoo.tools.profiler import profile


class JobCostSheet_Inherit(models.Model):
    _name = 'job.cost.sheet'
    _inherit = ['job.cost.sheet', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'number'
    _order = 'id DESC'
    _check_company_auto = True

    @api.constrains('project_id')
    def _check_existing_job_cost_sheet(self):
        for record in self:
            jcs = self.env['job.cost.sheet'].search(
                [('project_id', '=', record.project_id.id), ('state', 'not in', ['cancelled', 'reject', 'revised'])])
            if len(jcs) > 1:
                raise ValidationError(
                    _('The Job Cost Sheet for project "%s" already exists. Please use that job cost sheet or cancel it first and make a new one.' % (
                        (record.project_id.name))))

    @api.model
    def create(self, vals):
        vals['number'] = self.env['ir.sequence'].next_by_code('job.cost.sheet.sequence')
        return super(JobCostSheet_Inherit, self).create(vals)

    def write(self, vals):
        if 'default_material_line_ids' in self._context:
            self.env.context = dict(self.env.context)
            self.env.context.update({'default_material_line_ids': False})
        if 'default_labour_line_ids' in self._context:
            self.env.context = dict(self.env.context)
            self.env.context.update({'default_labour_line_ids': False})
        if 'default_overhead_line_ids' in self._context:
            self.env.context = dict(self.env.context)
            self.env.context.update({'default_overhead_line_ids': False})
        if 'default_equipment_line_ids' in self._context:
            self.env.context = dict(self.env.context)
            self.env.context.update({'default_equipment_line_ids': False})
        if 'default_subcon_line_ids' in self._context:
            self.env.context = dict(self.env.context)
            self.env.context.update({'default_subcon_line_ids': False})
        if 'default_internal_asset_line_ids' in self._context:
            self.env.context = dict(self.env.context)
            self.env.context.update({'default_internal_asset_line_ids': False})
        return super(JobCostSheet_Inherit, self).write(vals)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(JobCostSheet_Inherit, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if res.get('toolbar', False) and res.get('toolbar').get('print', False):
            reports = res.get('toolbar').get('print')
            for report in reports:
                res['toolbar']['print'].remove(report)

        return res

    number = fields.Char(string='Sheet Number', required=True, copy=False, readonly=True,
                         states={'draft': [('readonly', True)]}, index=True, default=lambda self: _('New'))

    job_reference = fields.Many2many('job.estimate', ondelete="cascade", string="BOQ Reference")
    partner_id = fields.Many2one('res.partner', string="Customer")
    account_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Group',
                                       domain="[('company_id', '=', company_id)]")
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
    hide_budget_left = fields.Boolean('Hide Budget Left', compute='_hide_budget')

    approved_date = fields.Datetime(string="Approved Date", tracking=True)

    is_empty_cost_sheet = fields.Boolean(string="Start with empty cost sheet")

    # create_uid = fields.Many2one('res.users', index=True)
    company_currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    sale_order_ref = fields.Many2many('sale.order.const', string='Sale Order Reference', tracking=True,
                                      ondelete='restrict')
    sale_const = fields.Many2one('sale.order.const', 'Sale Const')

    branch_id = fields.Many2one(related='project_id.branch_id', string="Branch",
                                default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids),
                                                     ('company_id', '=', self.env.company.id)])
    # add freeze state ----
    state = fields.Selection(selection_add=[('to_approve', 'Waiting For Approval'),
                                            ('approved', 'Approved'),
                                            ('in_progress', 'In Progress'),
                                            ('done', 'Done'),
                                            ('reject', 'Rejected'),
                                            ('freeze', 'Freeze'),
                                            ('cancelled', 'Cancelled'),
                                            ('revised', 'Revised')],
                             readonly=True, copy=False, index=True, tracking=True, default='draft', string="State", )
    state1 = fields.Selection(related='state', tracking=False)
    state2 = fields.Selection(related='state', tracking=False)
    state3 = fields.Selection(related='state', tracking=False)
    state4 = fields.Selection(related='state', tracking=False)

    active = fields.Boolean(string='Active', default=True)
    department_field = fields.Boolean(string='Type of Department', compute='_hide_fields')
    ba_freeze_state = fields.Boolean('Freeze State')

    # supplier
    supplier_id = fields.Char(string='Supplier')

    # table
    periodical_budget_ids = fields.One2many('project.budget', 'cost_sheet', string='Periodical Budget',
                                            states={'done': [('readonly', True)]})
    project_scope_cost_ids = fields.One2many('project.scope.cost', 'job_sheet_id', string='Project Scope Cost', )
    section_cost_ids = fields.One2many('section.cost', 'job_sheet_id', string='Section Cost', )
    material_gop_ids = fields.One2many('material.gop.material', 'job_sheet_id', string='Materials GOP',
                                       states={'done': [('readonly', True)]})
    material_ids = fields.One2many('material.material', 'job_sheet_id', string='Materials',
                                   states={'done': [('readonly', True)]})
    material_labour_gop_ids = fields.One2many('material.gop.labour', 'job_sheet_id', string='Labour GOP',
                                              states={'done': [('readonly', True)]})
    material_labour_ids = fields.One2many('material.labour', 'job_sheet_id', string='Labour',
                                          states={'done': [('readonly', True)]})
    material_overhead_gop_ids = fields.One2many('material.gop.overhead', 'job_sheet_id', string='Overhead GOP',
                                                states={'done': [('readonly', True)]})
    material_overhead_ids = fields.One2many('material.overhead', 'job_sheet_id', string='Overhead',
                                            states={'done': [('readonly', True)]})
    material_equipment_gop_ids = fields.One2many('material.gop.equipment', 'job_sheet_id', string='Equipment GOP',
                                                 states={'done': [('readonly', True)]})
    material_equipment_ids = fields.One2many('material.equipment', 'job_sheet_id', string='Equipment',
                                             states={'done': [('readonly', True)]})
    internal_asset_ids = fields.One2many('internal.asset', 'job_sheet_id', string='Internal Asset')
    material_subcon_gop_ids = fields.One2many('material.gop.subcon', 'job_sheet_id', string='Subcon GOP',
                                              states={'done': [('readonly', True)]})
    material_subcon_ids = fields.One2many('material.subcon', 'job_sheet_id', string='Subcon',
                                          states={'done': [('readonly', True)]})
    contract_history_ids = fields.One2many('contract.history', 'job_sheet_id', string='Contract History')
    internal_transfer_budget_line_ids = fields.One2many('internal.transfer.budget.line', 'job_sheet_id',
                                                        string='Internal Transfer Budget')
    history_itb_ids = fields.One2many('internal.transfer.budget.history', 'job_sheet_id',
                                      string='Internal Transfer Budget History')
    project_budget_transfer_line_ids = fields.One2many('project.budget.transfer.line', 'job_sheet_id',
                                                       string='Project Budget Transfer')
    history_pbt_ids = fields.One2many('project.budget.transfer.history', 'job_sheet_id',
                                      string='Project Budget Transfer History')
    change_allocation_line_cost_ids = fields.One2many('change.allocation.line.cost', 'job_sheet_id',
                                                      string='Change Allocation Line Cost')
    change_allocation_line_history_cost_ids = fields.One2many('change.allocation.line.history.cost', 'job_sheet_id',
                                                              string='Change Allocation Line History Cost')
    interwarehouse_transfer_history_ids = fields.One2many('interwarehouse.transfer.history', 'job_cost_sheet_id',
                                                          string="Inter-warehouse Transfer History")
    material_budget_claim_history_cost_ids = fields.One2many('budget.claim.history.cost', 'job_sheet_id',
                                                             string='Claimed Budget Left History',
                                                             domain=[('type', '=', 'material')])
    labour_budget_claim_history_cost_ids = fields.One2many('budget.claim.history.cost', 'job_sheet_id',
                                                           string='Claimed Budget Left History',
                                                           domain=[('type', '=', 'labour')])
    overhead_budget_claim_history_cost_ids = fields.One2many('budget.claim.history.cost', 'job_sheet_id',
                                                             string='Claimed Budget Left History',
                                                             domain=[('type', '=', 'overhead')])
    equipment_budget_claim_history_cost_ids = fields.One2many('budget.claim.history.cost', 'job_sheet_id',
                                                              string='Claimed Budget Left History',
                                                              domain=[('type', '=', 'equipment')])
    subcon_budget_claim_history_cost_ids = fields.One2many('budget.claim.history.cost', 'job_sheet_id',
                                                           string='Claimed Budget Left History',
                                                           domain=[('type', '=', 'subcon')])
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', related='project_id.warehouse_address')
    # amount material
    material_budget_res = fields.Monetary(string='Material Budget Reserved', compute='_amount_material', store=True)
    material_budget_pur = fields.Monetary(string='Material Budget Purchased', compute='_amount_material', store=True)
    material_budget_tra = fields.Monetary(string='Material Budget Transferred', compute='_amount_material', store=True)
    material_budget_left = fields.Monetary(string='Material Budget Left', compute='_amount_material', store=True)
    amount_material = fields.Monetary(string='Material Cost', compute='_amount_material', store=True)
    # material used/unused
    material_budget_unused = fields.Monetary(string='Material Budget Unused', compute='_amount_material', store=True)
    material_budget_used = fields.Monetary(string='Material Budget Used', compute='_amount_material', store=True)
    material_actual_cost = fields.Monetary(string='Material Actual Cost')
    # amount labour
    labour_budget_res = fields.Monetary(string='Labour Budget Reserved', compute='_amount_labour', store=True,
                                )
    labour_budget_pur = fields.Monetary(string='Labour Budget Purchased', compute='_amount_labour', store=True,
                                )
    labour_budget_tra = fields.Monetary(string='Labour Budget Transferred', compute='_amount_labour', store=True,
                                )
    labour_budget_left = fields.Monetary(string='Labour Budget Left', compute='_amount_labour', store=True,
                                    )
    amount_labour = fields.Monetary(string='Labour Cost', compute='_amount_labour', store=True)
    # labour used/unused
    labour_budget_unused = fields.Monetary(string='Labour Budget Unused', compute='_amount_labour', store=True,
                                    )
    labour_budget_used = fields.Monetary(string='Labour Budget Used', compute='_amount_labour', store=True,
                                    )
    labour_actual_cost = fields.Monetary(string='Labour Actual Cost')
    # amount overhead
    overhead_budget_res = fields.Monetary(string='Overhead Budget Reserved', compute='_amount_overhead', store=True,
                                    )
    overhead_budget_pur = fields.Monetary(string='Overhead Budget Purchased', compute='_amount_overhead', store=True,
                                    )
    overhead_budget_tra = fields.Monetary(string='Overhead Budget Transferred', compute='_amount_overhead', store=True,
                                    )
    overhead_budget_left = fields.Monetary(string='Overhead Budget Left', compute='_amount_overhead', store=True,
                                    )
    amount_overhead = fields.Monetary(string='Overhead Cost', readonly=True, compute='_amount_overhead', store=True)
    # overhead used/unused
    overhead_budget_unused = fields.Monetary(string='Overhead Budget Unused', compute='_amount_overhead', store=True,
                                        )
    overhead_budget_used = fields.Monetary(string='Overhead Budget Used', compute='_amount_overhead', store=True,
                                    )
    overhead_actual_cost = fields.Monetary(string='Overhead Actual Cost')
    # amount subcon
    subcon_budget_res = fields.Monetary(string='Subcon Budget Reserved', compute='_amount_subcon', store=True,
                                )
    subcon_budget_pur = fields.Monetary(string='Subcon Budget Purchased', compute='_amount_subcon', store=True,
                                )
    subcon_budget_left = fields.Monetary(string='Subcon Budget Left', compute='_amount_subcon', store=True,
                                    )
    amount_subcon = fields.Monetary(string='Subcon Cost', compute='_amount_subcon', store=True)
    # subcon used/unused
    subcon_budget_unused = fields.Monetary(string='Subcon Budget Unused', compute='_amount_subcon', store=True,
                                    )
    subcon_budget_used = fields.Monetary(string='Subcon Budget Used', compute='_amount_subcon', store=True,
                                    )
    subcon_actual_cost = fields.Monetary(string='Subcon Actual Cost', compute='_amount_subcon', store=True,
                                    )
    # amount equipment
    equipment_budget_res = fields.Monetary(string='Equipment Budget Reserved', compute='_amount_equipment', store=True,
                                    )
    equipment_budget_pur = fields.Monetary(string='Equipment Budget Purchased', compute='_amount_equipment', store=True,
                                    )
    equipment_budget_left = fields.Monetary(string='Equipment Budget Left', compute='_amount_equipment', store=True,
                                    )
    amount_equipment = fields.Monetary(string='Equipment Lease Cost', compute='_amount_equipment',
                                       store=True)
    # equipment used/unused
    equipment_budget_unused = fields.Monetary(string='Equipment Budget Unused', compute='_amount_equipment', store=True,
                                        )
    equipment_budget_used = fields.Monetary(string='Equipment Budget Used', compute='_amount_equipment', store=True,
                                    )
    equipment_actual_cost = fields.Monetary(string='Equipment Actual Cost')
    # amount internal asset
    internas_budget_left = fields.Monetary(string='Internal Asset Budget Left', compute='_amount_internal_asset',
                                           store=True,
                                    )
    amount_internal_asset = fields.Monetary(string='Internal Asset Cost', readonly=True,
                                            compute='_amount_internal_asset', store=True)
    # internal asset used/unused
    internas_budget_unused = fields.Monetary(string='Internal Asset Budget Unused', compute='_amount_internal_asset',
                                             store=True,
                                        )
    internas_budget_used = fields.Monetary(string='Internal Asset Budget Used', compute='_amount_internal_asset',
                                           store=True,
                                    )
    internas_actual_cost = fields.Monetary(string='Internal Asset Actual Cost')
    # internal budget transfer
    amount_free = fields.Float(string='Available Budget Amount', readonly=True, compute='_amount_free')
    amount_from_adjusted = fields.Float(string='Amount From Adjusting(+)', readonly=True,
                                        compute='_amount_free_adjusted')
    amount_from_project = fields.Float(string='Amount From Other Project(+)', readonly=True,
                                       compute='_amount_free_project')
    amount_send_project = fields.Float(string='Amount Send to Other Project(-)', readonly=True,
                                       compute='_amount_send_project')
    amount_from_budget = fields.Float(string='Amount From Periodical Budget (+)', readonly=True)

    # contract amount
    contract_budget_res = fields.Monetary(string='Total Budget Reserved', readonly=True, store=True,
                                          compute='_amount_contract')
    contract_budget_pur = fields.Monetary(string='Total Budget Purchased', readonly=True, store=True,
                                          compute='_amount_contract')
    contract_budget_tra = fields.Monetary(string='Total Budget Transferred', readonly=True, store=True,
                                          compute='_amount_contract')
    contract_budget_left = fields.Monetary(string='Total Budget Left', readonly=True, store=True,
                                           compute='_amount_contract')
    contract_budget_act = fields.Monetary(string='Total Actual Budget Left', readonly=True, store=True)
    amount_contract = fields.Monetary(string='Total Budget Contract', readonly=True,
                                      compute='_amount_contract')
    # contract amount used/unused
    contract_budget_unused = fields.Monetary(string='Total Budget Unused', readonly=True, store=True,
                                             compute='_amount_contract')
    contract_budget_used = fields.Monetary(string='Total Budget Used', readonly=True, store=True,
                                           fcompute='_amount_contract')
    contract_exp_revenue = fields.Monetary(string='Total Expected Revenue', readonly=True, store=True,
                                           compute='_amount_revenue')
    contract_exp_profit = fields.Monetary(string='Total Expected Profit', readonly=True, store=True,
                                          compute='_amount_revenue')
    # general
    amount_total = fields.Monetary(string='Total Cost', readonly=True, compute='_amount_total', store=True)

    # from contract
    amount_contract_material = fields.Monetary(string='Material', readonly=True, compute='_get_amount_total_contract',
                                               store=True)
    amount_contract_labour = fields.Monetary(string='Labour', readonly=True, compute='_get_amount_total_contract',
                                             store=True)
    amount_contract_overhead = fields.Monetary(string='Overhead', readonly=True, compute='_get_amount_total_contract',
                                               store=True)
    amount_contract_asset = fields.Monetary(string='Internal Asset', readonly=True,
                                            compute='_get_amount_total_contract', store=True)
    amount_contract_equipment = fields.Monetary(string='Equipment', readonly=True, compute='_get_amount_total_contract',
                                                store=True)
    amount_contract_subcon = fields.Monetary(string='Subcon', readonly=True, compute='_get_amount_total_contract',
                                             store=True)
    amount_contract_total = fields.Monetary(string='Total Contract', readonly=True,
                                            compute='_get_amount_total_contract', store=True)
    adjustment_sub = fields.Float(string="Adjustment (+)", readonly=True, compute='_get_amount_total_contract', store=True)
    discount_sub = fields.Float(string="Discount (-)", readonly=True, compute='_get_amount_total_contract', store=True)

    amount_contract_scope = fields.Monetary(string='Total Scope', readonly=True,
                                            compute='_get_amount_total_contract_scope_section', store=True)
    amount_contract_section = fields.Monetary(string='Total Section', readonly=True,
                                              compute='_get_amount_total_contract_scope_section', store=True)

    # smart button
    total_job_estimate = fields.Integer(string="BOQ", compute='_comute_job_estimate')
    total_sale_order = fields.Integer(string="Constract", compute='_comute_sales_orders')
    total_project_budget = fields.Integer(string="Periodical Budget", compute='_comute_project_budget')
    total_budget_change_request = fields.Integer(string="Budget Change Request",
                                                 compute='_comute_budget_change_request')
    total_project_budget_transfer = fields.Integer(string="Project Budget Transfer",
                                                   compute='_comute_project_budget_transfer')
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')
    cost_sheet_approval_matrix_line_ids = fields.One2many('cost.sheet.approval.matrix.line',
                                                          'cost_sheet_id',
                                                          string='Approval Matrix Line')
    # revision
    is_revision_created = fields.Boolean(string='Revision Created', copy=False)
    is_revision_cs = fields.Boolean(string="Revision Cost Sheet")
    main_revision_cs_id = fields.Many2one('job.cost.sheet', string='Main Revision Cost Sheet')
    revision_cs_id = fields.Many2one('job.cost.sheet', string='Revision Cost Sheet')
    revision_history_id = fields.Many2many("job.cost.sheet",
                                           relation="cs_revision_order_history",
                                           column1="cs_id",
                                           column2="revision_id",
                                           string="")
    revision_count = fields.Integer(string='Cost Sheet Revision Count', compute="get_revision_count")
    debug_mode = fields.Boolean(string="Debug Mode", compute="_compute_debug_mode")
    refresh_scope_section = fields.Boolean(string="Refresh Scope Section", compute="_compute_refresh_scope_section")
    custom_project_progress = fields.Selection(related='project_id.custom_project_progress', )

    def _compute_refresh_scope_section(self):
        for rec in self:
            rec.refresh_scope_section = True
            rec.set_scope_section_table()
            rec._get_amount_total_contract()
            rec._amount_material()
            # rec._get_amount_total_contract_scope_section()

    def _compute_debug_mode(self):
        for record in self:
            debug_mode = self.env.user.has_group('base.group_no_one')
            record.debug_mode = debug_mode
            return debug_mode

    def custom_menu(self):
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_director'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Cost Sheet',
                'res_model': 'job.cost.sheet',
                'view_mode': 'tree,form,pivot,graph',
                # 'views':views,
                'domain': [('department_type', '=', 'department'), ('project_id', 'in', self.env.user.project_ids.ids)],
                'context': {'default_department_type': 'department'},
                'help': """<p class="o_view_nocontent_smiling_face">
                    No Cost Sheet found. Let's create one!
                </p>
            """
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Cost Sheet',
                'res_model': 'job.cost.sheet',
                'view_mode': 'tree,form,pivot,graph',
                # 'views':views,
                'domain': [('department_type', '=', 'department')],
                'context': {'default_department_type': 'department'},
                'help': """<p class="o_view_nocontent_smiling_face">
                    No Cost Sheet found. Let's create one!
                </p>
            """
            }

    def custom_menu_management(self):
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
            'equip3_construction_accessright_setting.group_construction_director'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Cost Sheet',
                'res_model': 'job.cost.sheet',
                'view_mode': 'tree,form,pivot,graph',
                # 'views':views,
                'domain': [('department_type', '=', 'project'), ('project_id', 'in', self.env.user.project_ids.ids)],
                'context': {'default_department_type': 'project'},
                'help': """<p class="o_view_nocontent_smiling_face">
                    No Cost Sheet found. Let's create one!
                </p>
            """
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Cost Sheet',
                'res_model': 'job.cost.sheet',
                'view_mode': 'tree,form,pivot,graph',
                # 'views':views,
                'domain': [('department_type', '=', 'project')],
                'context': {'default_department_type': 'project'},
                'help': """<p class="o_view_nocontent_smiling_face">
                    No Cost Sheet found. Let's create one!
                </p>
            """
            }

    def action_cost_sheet_revision(self, default=None):
        self.state = 'revised'
        if self:
            self.ensure_one()
            self.is_revision_created = True
            if default is None:
                default = {}

            # Change number
            if self.is_revision_cs:
                cs_count = self.search(
                    [("main_revision_cs_id", '=', self.main_revision_cs_id.id), ('is_revision_cs', '=', True)])
                split_number = self.number.split('/')
                if split_number[-1].startswith('R'):
                    split_number[-1] = 'R%d' % (len(cs_count) + 1)
                else:
                    split_number.append('R%d' % (len(cs_count) + 1))
                number = '/'.join(split_number)
            else:
                cs_count = self.search([("main_revision_cs_id", '=', self.id), ('is_revision_cs', '=', True)])
                number = _('%s/R%d') % (self.number, len(cs_count) + 1)

            # Setting the default values for the new record.
            if 'number' not in default:
                default['state'] = 'draft'
                default['revision_cs_id'] = self.id
                default['is_revision_cs'] = True
                if self.is_revision_cs:
                    default['main_revision_cs_id'] = self.main_revision_cs_id.id
                else:
                    default['main_revision_cs_id'] = self.id
                default['is_revision_created'] = False
                default['revision_count'] = 0

            new_project_id = self.copy(default=default)
            # Contract History
            for contract_line in self.contract_history_ids:
                contract_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Material
            for material_line in self.material_ids:
                material_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            for material_gop in self.material_gop_ids:
                material_gop.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Labour
            for labour_line in self.material_labour_ids:
                labour_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            for labour_gop in self.material_labour_gop_ids:
                labour_gop.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Overhead
            for overhead_line in self.material_overhead_ids:
                overhead_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            for overhead_gop in self.material_overhead_gop_ids:
                overhead_gop.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Internal Asset
            for asset_line in self.internal_asset_ids:
                asset_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Equipment
            for equipment_line in self.material_equipment_ids:
                equipment_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            for equipment_gop in self.material_equipment_gop_ids:
                equipment_gop.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Subcon
            for subcon_line in self.material_subcon_ids:
                subcon_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            for subcon_gop in self.material_subcon_gop_ids:
                subcon_gop.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Approval Matrix Line
            for approval_line in self.cost_sheet_user_ids:
                approval_line.copy({
                    'cost_sheet_approver_id': new_project_id.id,
                })

            new_project_id.cost_sheet_user_ids = [(5, 0, 0)]
            new_project_id.write({'state': 'draft',
                                  'approved_user_ids': False,
                                  'approved_user': False,
                                  })
            new_project_id.onchange_approving_matrix_lines()

            if number.startswith('JCS'):
                new_project_id.number = number

            if self.is_revision_cs:
                new_project_id.revision_history_id = [(6, 0, self.main_revision_cs_id.ids + cs_count.ids)]
            else:
                new_project_id.revision_history_id = [(6, 0, self.ids)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Cost Sheet',
            'view_mode': 'form',
            'res_model': 'job.cost.sheet',
            'res_id': new_project_id.id,
            'target': 'current'
        }

    def get_revision_count(self):
        if self:
            for rec in self:
                rec.revision_count = 0
                qc = self.env['job.cost.sheet'].search([('revision_cs_id', '=', rec.id)])
                rec.revision_count = len(qc.ids)

    def open_revision_tree(self):
        revision = self.env['job.cost.sheet'].search([('revision_cs_id', '=', self.id)])
        action = self.env.ref('equip3_construction_operation.action_cost_sheet_revision').read()[0]
        action['context'] = {
            'domain': [('id', 'in', revision.ids)]
        }
        action['domain'] = [('id', 'in', revision.ids)]
        return action

    # approval matrix
    approval_matrix_id = fields.Many2one('approval.matrix.cost.sheet', string="Approval Matrix", store=True)
    approval_matrix_cs_line_ids = fields.One2many('approval.matrix.cost.sheet.line', 'cost_sheet_id', store=True,
                                                  string="Approved Matrix")
    cost_sheet_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                compute='is_cost_sheet_approval_matrix')
    is_approval_matrix_filled = fields.Boolean(string="Custome Matrix", store=False)
    user_is_approver = fields.Boolean(string='Is Approve Button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.cost.sheet.line',
                                              string='Cost Sheet Approval Matrix Line',
                                              store=False)

    approving_matrix_cost_id = fields.Many2one('approval.matrix.cost.sheet', string="Approval Matrix",
                                               compute='_compute_approving_customer_matrix', store=True)
    cost_sheet_user_ids = fields.One2many('cost.sheet.approver.user', 'cost_sheet_approver_id',
                                          string='Approver')
    approvers_ids = fields.Many2many('res.users', 'cost_sheet_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    employee_id = fields.Many2one('res.users', string='Users')
    last_approved = fields.Many2one('res.users', string='Users')
    is_over_budget_ratio = fields.Boolean(string="Over Budget Ratio")
    ratio_value = fields.Float(string="Ratio Value(%)")

    @api.depends('project_id')
    def is_cost_sheet_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        cost_sheet_approval_matrix = IrConfigParam.get_param('cost_sheet_approval_matrix')
        for record in self:
            record.cost_sheet_approval_matrix = cost_sheet_approval_matrix

    @api.depends('project_id', 'branch_id', 'company_id', 'department_type')
    def _compute_approving_customer_matrix(self):
        for res in self:
            res.approving_matrix_cost_id = False
            if res.cost_sheet_approval_matrix:
                if res.department_type == 'project':
                    approving_matrix_cost_id = self.env['approval.matrix.cost.sheet'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('project', 'in', (res.project_id.id)),
                        ('department_type', '=', 'project'),
                        ('set_default', '=', False)], limit=1)

                    approving_matrix_default = self.env['approval.matrix.cost.sheet'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('set_default', '=', True),
                        ('department_type', '=', 'project')], limit=1)

                else:
                    approving_matrix_cost_id = self.env['approval.matrix.cost.sheet'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('project', 'in', (res.project_id.id)),
                        ('department_type', '=', 'department'),
                        ('set_default', '=', False)], limit=1)

                    approving_matrix_default = self.env['approval.matrix.cost.sheet'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('set_default', '=', True),
                        ('department_type', '=', 'department')], limit=1)

                if approving_matrix_cost_id:
                    res.approving_matrix_cost_id = approving_matrix_cost_id and approving_matrix_cost_id.id or False
                else:
                    if approving_matrix_default:
                        res.approving_matrix_cost_id = approving_matrix_default and approving_matrix_default.id or False

    @api.onchange('project_id', 'approving_matrix_cost_id')
    def onchange_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.project_id:
                app_list = []
                if record.state == 'draft' and record.cost_sheet_approval_matrix:
                    record.cost_sheet_user_ids = []
                    for rec in record.approving_matrix_cost_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'user_ids': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                    record.approvers_ids = app_list
                    record.cost_sheet_user_ids = data
                else:
                    pass

    def _compute_is_approver(self):
        for record in self:
            if record.approvers_ids:
                current_user = record.env.user
                matrix_line = sorted(record.cost_sheet_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(record.cost_sheet_user_ids)
                if app < a:
                    for line in record.cost_sheet_user_ids[app]:
                        if current_user in line.user_ids:
                            record.is_approver = True
                        else:
                            record.is_approver = False
                else:
                    record.is_approver = False
            else:
                record.is_approver = False

    def request_approval(self, is_continue=False):
        if not self.material_ids and not self.material_labour_ids and not self.material_overhead_ids and not self.material_subcon_ids and not self.material_equipment_ids:
            raise ValidationError(_("Add at least one material for estimation."))
        elif self.amount_free < 0 and not is_continue:
            # raise ValidationError(_("Cost amount cannot be over the contract amount."))
            return {
                'name': _('Warning'),
                'type': 'ir.actions.act_window',
                'res_model': 'cost.sheet.validation.wizard',
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {
                    'default_cost_sheet_id': self.id,
                    'default_is_approval_matrix': True,
                }
            }

        if len(self.cost_sheet_user_ids) == 0:
            raise ValidationError(
                _("There's no cost sheet approval matrix for this project or approval matrix default created. You have to create it first."))

        for record in self:
            action_id = self.env.ref('equip3_construction_operation.action_view_job_cost_sheet_menu')
            template_id = self.env.ref('equip3_construction_operation.email_template_reminder_for_cost_sheet')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=job.cost.sheet'
            if record.cost_sheet_user_ids and len(record.cost_sheet_user_ids[0].user_ids) > 1:
                for approved_matrix_id in record.cost_sheet_user_ids[0].user_ids:
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
                approver = record.cost_sheet_user_ids[0].user_ids[0]
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

            for line in record.cost_sheet_user_ids:
                line.write({'approver_state': 'draft'})

    def action_approved(self):
        if not self.material_ids and not self.material_labour_ids and not self.material_overhead_ids and not self.material_subcon_ids and not self.material_equipment_ids:
            raise ValidationError(_("Add at least one material for estimation."))
        # elif self.amount_free < 0:
        #     raise ValidationError(_("Cost amount cannot be over the contract amount."))

        sequence_matrix = [data.name for data in self.cost_sheet_user_ids]
        sequence_approval = [data.name for data in self.cost_sheet_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.cost_sheet_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)

        for record in self:
            action_id = self.env.ref('equip3_construction_operation.action_view_job_cost_sheet_menu')
            template_app = self.env.ref('equip3_construction_operation.email_template_cost_sheet_approved')
            template_id = self.env.ref('equip3_construction_operation.email_template_reminder_for_cost_sheet_temp')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=job.cost.sheet'

            current_user = self.env.uid
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"

            if self.env.user not in record.approved_user_ids:
                if record.is_approver:
                    for line in record.cost_sheet_user_ids:
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

                    matrix_line = sorted(record.cost_sheet_user_ids.filtered(lambda r: r.is_approve == False))
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
            action_id = self.env.ref('equip3_construction_operation.action_view_job_cost_sheet_menu')
            template_rej = self.env.ref('equip3_construction_operation.email_template_cost_sheet_rejected')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=job.cost.sheet'
            for user in record.cost_sheet_user_ids:
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

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'approval.matrix.cost.sheet.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_in_progress(self, is_continue=False):
        if not self.material_ids and not self.material_labour_ids and not self.material_overhead_ids and not self.material_subcon_ids and not self.material_equipment_ids:
            raise ValidationError(_("Add at least one material for estimation."))
        if self.amount_free < 0 and not is_continue:
            return {
                'name': _('Warning'),
                'type': 'ir.actions.act_window',
                'res_model': 'cost.sheet.validation.wizard',
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {
                    'default_cost_sheet_id': self.id,
                    'default_is_approval_matrix': False,
                }
            }
        else:
            context = {
                'default_project_id': self.project_id.id,
                'default_job_sheet_id': self.id,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'In Progress Cost Sheet Wizard',
                'view_mode': 'form',
                'res_model': 'cost.sheet.approval.wizard',
                'target': 'new',
                'context': context
            }
            # return self.write({'state': 'approved', 'approved_date' : datetime.now()})

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
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

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('project_id')
    def _get_customer(self):
        for proj in self.project_id:
            self.partner_id = proj.partner_id.id
            self.account_tag_ids = proj.analytic_idz

    def _hide_budget(self):
        for res in self:
            if res.budgeting_method == 'product_budget':
                res.hide_budget_left = False
            else:
                res.hide_budget_left = True

    def _hide_fields(self):
        for res in self:
            if res.department_type == 'department':
                res.department_field = False
            else:
                res.department_field = True

    def get_so_line_condition(self, scope_new_data, section_new_data, data, scope_data, section_data, line,
                              line_product_id):
        return [
            scope_new_data.id == scope_data.id,
            section_new_data.id == section_data.id,
            data[2].get('group_of_product') == line.group_of_product.id,
            data[2].get('product_id') == line_product_id.id,
            data[2].get('description') == line.description,
            data[2].get('uom_id') == line.uom_id.id,
        ]

    def prepare_material_so(self, item):
        return {
            'project_scope': item.project_scope.id,
            'section_name': item.section_name.id,
            'variable_ref': item.variable_ref.id,
            'group_of_product': item.group_of_product.id,
            'product_id': item.material_id.id,
            'description': item.description,
            'product_qty': item.quantity,
            'uom_id': item.uom_id.id,
            'price_unit': item.unit_price,
            'material_amount_total': item.subtotal,
        }

    def prepare_labour_so(self, item):
        return {
            'project_scope': item.project_scope.id,
            'section_name': item.section_name.id,
            'variable_ref': item.variable_ref.id,
            'group_of_product': item.group_of_product.id,
            'product_id': item.labour_id.id,
            'description': item.description,
            'product_qty': item.quantity,
            'uom_id': item.uom_id.id,
            'price_unit': item.unit_price,
            'labour_amount_total': item.subtotal,
        }

    def prepare_subcon_so(self, item):
        return {
            'project_scope': item.project_scope.id,
            'section_name': item.section_name.id,
            'variable_ref': item.variable_ref.id,
            'variable': item.subcon_id.id,
            'description': item.description,
            'product_qty': item.quantity,
            'uom_id': item.uom_id.id,
            'price_unit': item.unit_price,
            'subcon_amount_total': item.subtotal,
        }

    def prepare_overhead_so(self, item):
        return {
            'project_scope': item.project_scope.id,
            'section_name': item.section_name.id,
            'variable_ref': item.variable_ref.id,
            'overhead_catagory': item.overhead_catagory,
            'group_of_product': item.group_of_product.id,
            'product_id': item.overhead_id.id,
            'description': item.description,
            'product_qty': item.quantity,
            'uom_id': item.uom_id.id,
            'price_unit': item.unit_price,
            'overhead_amount_total': item.subtotal,
        }

    def prepare_asset_so(self, item):
        return {
            'project_scope': item.project_scope.id,
            'section_name': item.section_name.id,
            'variable_ref': item.variable_ref.id,
            'asset_category_id': item.asset_category_id.id,
            'asset_id': item.asset_id.id,
            'description': item.description,
            'budgeted_qty': item.quantity,
            'uom_id': item.uom_id.id,
            'price_unit': item.unit_price,
            'budgeted_amt': item.subtotal,
        }

    def prepare_equipment_so(self, item):
        return {
            'project_scope': item.project_scope.id,
            'section_name': item.section_name.id,
            'variable_ref': item.variable_ref.id,
            'group_of_product': item.group_of_product.id,
            'product_id': item.equipment_id.id,
            'description': item.description,
            'product_qty': item.quantity,
            'uom_id': item.uom_id.id,
            'price_unit': item.unit_price,
            'equipment_amount_total': item.subtotal,
        }

    def _sales_order_onchange(self):
        if self.sale_order_ref:
            sale = self.sale_order_ref
            # Material
            self.material_ids = [(5, 0, 0)]
            product_budget_dict = {}
            for item in sale.material_line_ids:
                # key_product_budget_product = project_scope + section_name + group_of_product + product_id + description + uom
                key_product_budget_product = str(item.project_scope.id) + str(item.section_name.id) + str(
                    item.group_of_product.id) + str(item.material_id.id) + item.description + str(item.uom_id.id)
                if product_budget_dict.get(key_product_budget_product, False):
                    product_budget_dict[key_product_budget_product]['product_qty'] += item.quantity
                    product_budget_dict[key_product_budget_product]['material_amount_total'] += item.subtotal
                else:
                    product_budget_dict[key_product_budget_product] = self.prepare_material_so(item)

            self.material_ids = [(0, 0, item) for k, item in product_budget_dict.items()]

            # Labour
            self.material_labour_ids = [(5, 0, 0)]
            product_budget_dict = {}
            for item in sale.labour_line_ids:
                # key_product_budget_product = project_scope + section_name + group_of_product + product_id + description + uom
                key_product_budget_product = str(item.project_scope.id) + str(item.section_name.id) + str(
                    item.group_of_product.id) + str(item.labour_id.id) + item.description + str(item.uom_id.id)
                if product_budget_dict.get(key_product_budget_product, False):
                    product_budget_dict[key_product_budget_product]['product_qty'] += item.quantity
                    product_budget_dict[key_product_budget_product]['labour_amount_total'] += item.subtotal
                else:
                    product_budget_dict[key_product_budget_product] = self.prepare_labour_so(item)

            self.material_labour_ids = [(0, 0, item) for k, item in product_budget_dict.items()]
            # get time & contractors
            job_estimate_labour = {}
            for job_estimate in sale.job_references:
                for labour in job_estimate.labour_estimation_ids:
                    key = str(labour.project_scope.id) + str(labour.section_name.id) + str(
                        labour.group_of_product.id) + str(labour.product_id.id) + labour.description + str(
                        labour.uom_id.id)
                    if key in job_estimate_labour:
                        job_estimate_labour[key]['time'] += labour.time
                        job_estimate_labour[key]['contractors'] += labour.contractors
                    else:
                        job_estimate_labour[key] = {
                            'time': labour.time,
                            'contractors': labour.contractors,
                        }

            for labour in self.material_labour_ids:
                key = str(labour.project_scope.id) + str(labour.section_name.id) + str(
                    labour.group_of_product.id) + str(labour.product_id.id) + labour.description + str(labour.uom_id.id)
                if key in job_estimate_labour:
                    labour.time = job_estimate_labour[key]['time']
                    labour.contractors = job_estimate_labour[key]['contractors']

            # Subcon
            self.material_subcon_ids = [(5, 0, 0)]
            product_budget_dict = {}
            for item in sale.subcon_line_ids:
                # key_product_budget_product = project_scope + section_name + variable + description + uom
                key_product_budget_product = str(item.project_scope.id) + str(item.section_name.id) + str(
                    item.subcon_id.id) + item.description + str(item.uom_id.id)
                if product_budget_dict.get(key_product_budget_product, False):
                    product_budget_dict[key_product_budget_product]['product_qty'] += item.quantity
                    product_budget_dict[key_product_budget_product]['subcon_amount_total'] += item.subtotal
                else:
                    product_budget_dict[key_product_budget_product] = self.prepare_subcon_so(item)

            self.material_subcon_ids = [(0, 0, item) for k, item in product_budget_dict.items()]

            # Overhead
            self.material_overhead_ids = [(5, 0, 0)]
            product_budget_dict = {}
            for item in sale.overhead_line_ids:
                # key_product_budget_product = project_scope + section_name + overhead_catagory + group_of_product + product_id + description + uom
                key_product_budget_product = str(item.project_scope.id) + str(item.section_name.id) + str(
                    item.overhead_catagory) + str(item.group_of_product.id) + str(
                    item.overhead_id.id) + item.description + str(item.uom_id.id)
                if product_budget_dict.get(key_product_budget_product, False):
                    product_budget_dict[key_product_budget_product]['product_qty'] += item.quantity
                    product_budget_dict[key_product_budget_product]['overhead_amount_total'] += item.subtotal
                else:
                    product_budget_dict[key_product_budget_product] = self.prepare_overhead_so(item)

            self.material_overhead_ids = [(0, 0, item) for k, item in product_budget_dict.items()]

            # Internal Asset
            self.internal_asset_ids = [(5, 0, 0)]
            product_budget_dict = {}
            for item in sale.internal_asset_line_ids:
                # key_product_budget_product = project_scope + section_name + asset_category_id + asset_id + description + uom
                key_product_budget_product = str(item.project_scope.id) + str(item.section_name.id) + str(
                    item.asset_category_id.id) + str(item.asset_id.id) + item.description + str(item.uom_id.id)
                if product_budget_dict.get(key_product_budget_product, False):
                    product_budget_dict[key_product_budget_product]['budgeted_qty'] += item.quantity
                    product_budget_dict[key_product_budget_product]['budgeted_amt'] += item.subtotal
                else:
                    product_budget_dict[key_product_budget_product] = self.prepare_asset_so(item)

            self.internal_asset_ids = [(0, 0, item) for k, item in product_budget_dict.items()]

            # Equipment
            self.material_equipment_ids = [(5, 0, 0)]
            product_budget_dict = {}
            for item in sale.equipment_line_ids:
                # key_product_budget_product = project_scope + section_name + group_of_product + product_id + description + uom
                key_product_budget_product = str(item.project_scope.id) + str(item.section_name.id) + str(
                    item.group_of_product.id) + str(item.equipment_id.id) + item.description + str(item.uom_id.id)
                if product_budget_dict.get(key_product_budget_product, False):
                    product_budget_dict[key_product_budget_product]['product_qty'] += item.quantity
                    product_budget_dict[key_product_budget_product]['equipment_amount_total'] += item.subtotal
                else:
                    product_budget_dict[key_product_budget_product] = self.prepare_equipment_so(item)

            self.material_equipment_ids = [(0, 0, item) for k, item in product_budget_dict.items()]

    def get_scope_cost_value(self, scope_dict, key_scope, field_scope, field_budget, field_budget_left,
                             field_reserved_amount, field_billed_amount,
                             field_paid_amount, field_transferred_amount, field_unused_amount, field_actual_used_amount,
                             field_allocated_budget_amount, field_unallocated_amount):
        temp_scope_dict = scope_dict
        if temp_scope_dict.get(key_scope, False):
            temp_scope_dict[key_scope]['subtotal'] += field_budget
            temp_scope_dict[key_scope]['budget_amt_left'] += field_budget_left
            temp_scope_dict[key_scope]['reserved_amt'] += field_reserved_amount
            temp_scope_dict[key_scope]['billed_amt'] += field_billed_amount
            temp_scope_dict[key_scope]['paid_amt'] += field_paid_amount
            temp_scope_dict[key_scope]['transferred_amt'] += field_transferred_amount
            temp_scope_dict[key_scope]['unused_amount'] += field_unused_amount
            temp_scope_dict[key_scope]['actual_used_amt'] += field_actual_used_amount
            temp_scope_dict[key_scope]['allocated_budget_amt'] += field_allocated_budget_amount
            temp_scope_dict[key_scope]['unallocated_amount'] += field_unallocated_amount
        else:
            temp_scope_dict[key_scope] = {
                'project_scope_id': field_scope,
                'subtotal': field_budget,
                'budget_amt_left': field_budget_left,
                'reserved_amt': field_reserved_amount,
                'billed_amt': field_billed_amount,
                'paid_amt': field_paid_amount,
                'transferred_amt': field_transferred_amount,
                'unused_amount': field_unused_amount,
                'actual_used_amt': field_actual_used_amount,
                'allocated_budget_amt': field_allocated_budget_amount,
                'unallocated_amount': field_unallocated_amount,
            }
        return temp_scope_dict

    def get_section_cost_value(self, section_dict, key_section, field_scope, field_section, field_budget,
                               field_budget_left, field_reserved_amount, field_billed_amount,
                               field_paid_amount, field_transferred_amount, field_unused_amount,
                               field_actual_used_amount,
                               field_allocated_budget_amount, field_unallocated_amount):
        temp_section_dict = section_dict
        if temp_section_dict.get(key_section, False):
            temp_section_dict[key_section]['subtotal'] += field_budget
            temp_section_dict[key_section]['budget_amt_left'] += field_budget_left
            temp_section_dict[key_section]['reserved_amt'] += field_reserved_amount
            temp_section_dict[key_section]['billed_amt'] += field_billed_amount
            temp_section_dict[key_section]['paid_amt'] += field_paid_amount
            temp_section_dict[key_section]['transferred_amt'] += field_transferred_amount
            temp_section_dict[key_section]['unused_amount'] += field_unused_amount
            temp_section_dict[key_section]['actual_used_amt'] += field_actual_used_amount
            temp_section_dict[key_section]['allocated_budget_amt'] += field_allocated_budget_amount
            temp_section_dict[key_section]['unallocated_amount'] += field_unallocated_amount
        else:
            temp_section_dict[key_section] = {
                'project_scope_id': field_scope,
                'section_id': field_section,
                'subtotal': field_budget,
                'budget_amt_left': field_budget_left,
                'reserved_amt': field_reserved_amount,
                'billed_amt': field_billed_amount,
                'paid_amt': field_paid_amount,
                'transferred_amt': field_transferred_amount,
                'unused_amount': field_unused_amount,
                'actual_used_amt': field_actual_used_amount,
                'allocated_budget_amt': field_allocated_budget_amount,
                'unallocated_amount': field_unallocated_amount,
            }
        return temp_section_dict

    @api.onchange('material_ids', 'material_labour_ids', 'material_overhead_ids', 'material_subcon_ids',
                  'material_equipment_ids', 'internal_asset_ids')
    def set_scope_section_table(self):
        for rec in self:
            # if len(rec.project_scope_cost_ids) == 0:
            #     rec.project_scope_cost_ids = [(5, 0, 0)]
            # if len(rec.section_cost_ids) == 0:
            #     rec.section_cost_ids = [(5, 0, 0)]

            scope_dict = {}
            section_dict = {}

            # This context is used when creating new quotation from wizard
            # Will conflict with this onchange
            if 'default_material_line_ids' in self._context:
                self.env.context = dict(self.env.context)
                self.env.context.update({'default_material_line_ids': False})
            if 'default_labour_line_ids' in self._context:
                self.env.context = dict(self.env.context)
                self.env.context.update({'default_labour_line_ids': False})
            if 'default_overhead_line_ids' in self._context:
                self.env.context = dict(self.env.context)
                self.env.context.update({'default_overhead_line_ids': False})
            if 'default_equipment_line_ids' in self._context:
                self.env.context = dict(self.env.context)
                self.env.context.update({'default_equipment_line_ids': False})
            if 'default_subcon_line_ids' in self._context:
                self.env.context = dict(self.env.context)
                self.env.context.update({'default_subcon_line_ids': False})
            if 'default_internal_asset_line_ids' in self._context:
                self.env.context = dict(self.env.context)
                self.env.context.update({'default_internal_asset_line_ids': False})

            # contract = rec.contract_history_ids.filtered(lambda r: r.contract_category == 'main').contract_history
            if rec.project_id:

                for section in rec.project_id.project_section_ids:
                    key_scope = str(section.project_scope.id)
                    key_section = str(section.project_scope.id) + str(section.section.id)

                    scope_dict = self.get_scope_cost_value(scope_dict, key_scope, section.project_scope.id,
                                                           0, 0,
                                                           0, 0,
                                                           0,
                                                           0, 0,
                                                           0, 0,
                                                           0)

                    section_dict = self.get_section_cost_value(section_dict, key_section, section.project_scope.id,
                                                               section.section.id, 0,
                                                               0, 0,
                                                               0, 0,
                                                               0, 0,
                                                               0, 0,
                                                               0)

            for material in rec.material_ids:
                key_scope = str(material.project_scope.id)
                key_section = str(material.project_scope.id) + str(material.section_name.id)

                scope_dict = self.get_scope_cost_value(scope_dict, key_scope, material.project_scope.id,
                                                       material.material_amount_total, material.budgeted_amt_left,
                                                       material.reserved_amt, material.billed_amt,
                                                       material.purchased_amt,
                                                       material.transferred_amt, material.unused_amt,
                                                       material.actual_used_amt, material.allocated_budget_amt,
                                                       material.product_amt_na)
                section_dict = self.get_section_cost_value(section_dict, key_section, material.project_scope.id,
                                                           material.section_name.id, material.material_amount_total,
                                                           material.budgeted_amt_left, material.reserved_amt,
                                                           material.billed_amt, material.purchased_amt,
                                                           material.transferred_amt, material.unused_amt,
                                                           material.actual_used_amt, material.allocated_budget_amt,
                                                           material.product_amt_na)

            for labour in rec.material_labour_ids:
                key_scope = str(labour.project_scope.id)
                key_section = str(labour.project_scope.id) + str(labour.section_name.id)

                scope_dict = self.get_scope_cost_value(scope_dict, key_scope, labour.project_scope.id,
                                                       labour.labour_amount_total, labour.budgeted_amt_left,
                                                       labour.reserved_amt, labour.billed_amt, labour.purchased_amt,
                                                       labour.transferred_amt, labour.unused_amt,
                                                       labour.actual_used_amt,
                                                       labour.allocated_budget_amt, labour.product_amt_na)
                section_dict = self.get_section_cost_value(section_dict, key_section, labour.project_scope.id,
                                                           labour.section_name.id, labour.labour_amount_total,
                                                           labour.budgeted_amt_left,
                                                           labour.reserved_amt, labour.billed_amt, labour.purchased_amt,
                                                           labour.transferred_amt, labour.unused_amt,
                                                           labour.actual_used_amt,
                                                           labour.allocated_budget_amt, labour.product_amt_na)

            for overhead in rec.material_overhead_ids:
                key_scope = str(overhead.project_scope.id)
                key_section = str(overhead.project_scope.id) + str(overhead.section_name.id)

                scope_dict = self.get_scope_cost_value(scope_dict, key_scope, overhead.project_scope.id,
                                                       overhead.overhead_amount_total, overhead.budgeted_amt_left,
                                                       overhead.reserved_amt, overhead.billed_amt,
                                                       overhead.purchased_amt, overhead.transferred_amt,
                                                       overhead.unused_amt,
                                                       overhead.actual_used_amt, overhead.allocated_budget_amt,
                                                       overhead.product_amt_na)
                section_dict = self.get_section_cost_value(section_dict, key_section, overhead.project_scope.id,
                                                           overhead.section_name.id, overhead.overhead_amount_total,
                                                           overhead.budgeted_amt_left,
                                                           overhead.reserved_amt, overhead.billed_amt,
                                                           overhead.purchased_amt, overhead.transferred_amt,
                                                           overhead.unused_amt,
                                                           overhead.actual_used_amt, overhead.allocated_budget_amt,
                                                           overhead.product_amt_na)

            for subcon in rec.material_subcon_ids:
                key_scope = str(subcon.project_scope.id)
                key_section = str(subcon.project_scope.id) + str(subcon.section_name.id)

                scope_dict = self.get_scope_cost_value(scope_dict, key_scope, subcon.project_scope.id,
                                                       subcon.subcon_amount_total, subcon.budgeted_amt_left,
                                                       subcon.reserved_amt,
                                                       subcon.billed_amt, subcon.purchased_amt, 0,
                                                       subcon.unused_amt, subcon.actual_used_amt,
                                                       subcon.allocated_budget_amt, subcon.product_amt_na)
                section_dict = self.get_section_cost_value(section_dict, key_section, subcon.project_scope.id,
                                                           subcon.section_name.id, subcon.subcon_amount_total,
                                                           subcon.budgeted_amt_left,
                                                           subcon.reserved_amt,
                                                           subcon.billed_amt, subcon.purchased_amt,
                                                           0,
                                                           subcon.unused_amt, subcon.actual_used_amt,
                                                           subcon.allocated_budget_amt, subcon.product_amt_na)

            for equipment in rec.material_equipment_ids:
                key_scope = str(equipment.project_scope.id)
                key_section = str(equipment.project_scope.id) + str(equipment.section_name.id)

                scope_dict = self.get_scope_cost_value(scope_dict, key_scope, equipment.project_scope.id,
                                                       equipment.equipment_amount_total, equipment.budgeted_amt_left,
                                                       equipment.reserved_amt, equipment.billed_amt,
                                                       equipment.purchased_amt, 0,
                                                       equipment.unused_amt, equipment.actual_used_amt,
                                                       equipment.allocated_budget_amt, equipment.product_amt_na)
                section_dict = self.get_section_cost_value(section_dict, key_section, equipment.project_scope.id,
                                                           equipment.section_name.id, equipment.equipment_amount_total,
                                                           equipment.budgeted_amt_left,
                                                           equipment.reserved_amt, equipment.billed_amt,
                                                           equipment.purchased_amt, 0,
                                                           equipment.unused_amt, equipment.actual_used_amt,
                                                           equipment.allocated_budget_amt, equipment.product_amt_na)

            for asset in rec.internal_asset_ids:
                key_scope = str(asset.project_scope.id)
                key_section = str(asset.project_scope.id) + str(asset.section_name.id)

                scope_dict = self.get_scope_cost_value(scope_dict, key_scope, asset.project_scope.id,
                                                       asset.budgeted_amt, asset.budgeted_amt_left,
                                                       0, 0, 0, 0,
                                                       asset.unused_amt,
                                                       asset.actual_used_amt, asset.allocated_budget_amt,
                                                       asset.unallocated_amt)

                section_dict = self.get_section_cost_value(section_dict, key_section, asset.project_scope.id,
                                                           asset.section_name.id, asset.budgeted_amt,
                                                           asset.budgeted_amt_left,
                                                           0, 0, 0, 0,
                                                           asset.unused_amt,
                                                           asset.actual_used_amt, asset.allocated_budget_amt,
                                                           asset.unallocated_amt)
            if len(rec.project_scope_cost_ids) != len(rec.project_id.project_scope_ids):
                rec.project_scope_cost_ids = [(5, 0, 0)]
                rec.project_scope_cost_ids = [(0, 0, item) for key, item in scope_dict.items()]
            else:
                for scope in scope_dict.values():
                    scope_line = rec.project_scope_cost_ids.filtered(
                        lambda r: r.project_scope_id.id == scope['project_scope_id'])
                    if scope_line:
                        scope_line.subtotal = scope['subtotal']
                        scope_line.budget_amt_left = scope['budget_amt_left']
                        scope_line.reserved_amt = scope['reserved_amt']
                        scope_line.billed_amt = scope['billed_amt']
                        scope_line.paid_amt = scope['paid_amt']
                        scope_line.transferred_amt = scope['transferred_amt']
                        scope_line.unused_amount = scope['unused_amount']
                        scope_line.actual_used_amt = scope['actual_used_amt']
                        scope_line.allocated_budget_amt = scope['allocated_budget_amt']
                        scope_line.unallocated_amount = scope['unallocated_amount']

            if len(rec.section_cost_ids) != len(rec.project_id.project_section_ids):
                rec.section_cost_ids = [(5, 0, 0)]
                rec.section_cost_ids = [(0, 0, item) for k, item in section_dict.items()]
            else:
                for section in section_dict.values():
                    section_line = rec.section_cost_ids.filtered(
                        lambda r: r.project_scope_id.id == section['project_scope_id'] and r.section_id.id == section[
                            'section_id'])
                    if section_line:
                        section_line.subtotal = section['subtotal']
                        section_line.budget_amt_left = section['budget_amt_left']
                        section_line.reserved_amt = section['reserved_amt']
                        section_line.billed_amt = section['billed_amt']
                        section_line.paid_amt = section['paid_amt']
                        section_line.transferred_amt = section['transferred_amt']
                        section_line.unused_amount = section['unused_amount']
                        section_line.actual_used_amt = section['actual_used_amt']
                        section_line.allocated_budget_amt = section['allocated_budget_amt']
                        section_line.unallocated_amount = section['unallocated_amount']

    @api.onchange('material_ids')
    def get_gop_material_table(self):
        self.material_gop_ids = [(5, 0, 0)]
        gop_budget_dict = {}
        for item in self.material_ids:
            # key_gop_budget = project_scope + section_name + group_of_product
            key_gop_budget = str(item.project_scope.id) + str(item.section_name.id) + str(item.group_of_product.id)
            if gop_budget_dict.get(key_gop_budget, False):
                gop_budget_dict[key_gop_budget]['material_gop_amount_total'] += item.material_amount_total
                gop_budget_dict[key_gop_budget]['actual_used_amt'] += item.actual_used_amt
                gop_budget_dict[key_gop_budget]['reserved_amt'] += item.reserved_amt
                gop_budget_dict[key_gop_budget]['allocated_budget_amt'] += item.allocated_budget_amt
                gop_budget_dict[key_gop_budget]['billed_amt'] += item.billed_amt
                gop_budget_dict[key_gop_budget]['purchased_amt'] += item.purchased_amt
            else:
                gop_budget_dict[key_gop_budget] = {
                    'project_scope': item.project_scope.id,
                    'section_name': item.section_name.id,
                    'group_of_product': item.group_of_product.id,
                    'material_gop_amount_total': item.material_amount_total,
                    'actual_used_amt': item.actual_used_amt,
                    'reserved_amt': item.reserved_amt,
                    'allocated_budget_amt': item.allocated_budget_amt,
                    'billed_amt': item.billed_amt,
                    'purchased_amt': item.purchased_amt,
                }

        # This context is used when creating new quotation from wizard
        # Will conflict with this onchange
        if 'default_material_line_ids' in self._context:
            self.env.context = dict(self.env.context)
            self.env.context.update({'default_material_line_ids': False})

        self.material_gop_ids = [(0, 0, item) for k, item in gop_budget_dict.items()]

    @api.onchange('material_labour_ids')
    def get_gop_labour_table(self):
        self.material_labour_gop_ids = [(5, 0, 0)]
        gop_budget_dict = {}
        for item in self.material_labour_ids:
            # key_gop_budget = project_scope + section_name + group_of_product
            key_gop_budget = str(item.project_scope.id) + str(item.section_name.id) + str(item.group_of_product.id)
            if gop_budget_dict.get(key_gop_budget, False):
                gop_budget_dict[key_gop_budget]['labour_gop_amount_total'] += item.labour_amount_total
                gop_budget_dict[key_gop_budget]['actual_used_amt'] += item.actual_used_amt
                gop_budget_dict[key_gop_budget]['reserved_amt'] += item.reserved_amt
                gop_budget_dict[key_gop_budget]['allocated_budget_amt'] += item.allocated_budget_amt
                gop_budget_dict[key_gop_budget]['billed_amt'] += item.billed_amt
                gop_budget_dict[key_gop_budget]['purchased_amt'] += item.purchased_amt
            else:
                gop_budget_dict[key_gop_budget] = {
                    'project_scope': item.project_scope.id,
                    'section_name': item.section_name.id,
                    'group_of_product': item.group_of_product.id,
                    'labour_gop_amount_total': item.labour_amount_total,
                    'actual_used_amt': item.actual_used_amt,
                    'reserved_amt': item.reserved_amt,
                    'allocated_budget_amt': item.allocated_budget_amt,
                    'billed_amt': item.billed_amt,
                    'purchased_amt': item.purchased_amt,
                }

        # This context is used when creating new quotation from wizard
        # Will conflict with this onchange
        if 'default_labour_line_ids' in self._context:
            self.env.context = dict(self.env.context)
            self.env.context.update({'default_labour_line_ids': False})

        self.material_labour_gop_ids = [(0, 0, item) for k, item in gop_budget_dict.items()]

    @api.onchange('material_overhead_ids')
    def get_gop_overhead_table(self):
        self.material_overhead_gop_ids = [(5, 0, 0)]
        gop_budget_dict = {}
        for item in self.material_overhead_ids:
            # key_gop_budget = project_scope + section_name + group_of_product
            key_gop_budget = str(item.project_scope.id) + str(item.section_name.id) + str(item.group_of_product.id)
            if gop_budget_dict.get(key_gop_budget, False):
                gop_budget_dict[key_gop_budget]['overhead_gop_amount_total'] += item.overhead_amount_total
                gop_budget_dict[key_gop_budget]['actual_used_amt'] += item.actual_used_amt
                gop_budget_dict[key_gop_budget]['reserved_amt'] += item.reserved_amt
                gop_budget_dict[key_gop_budget]['allocated_budget_amt'] += item.allocated_budget_amt
                gop_budget_dict[key_gop_budget]['billed_amt'] += item.billed_amt
                gop_budget_dict[key_gop_budget]['purchased_amt'] += item.purchased_amt
            else:
                gop_budget_dict[key_gop_budget] = {
                    'project_scope': item.project_scope.id,
                    'section_name': item.section_name.id,
                    'variable_ref': item.variable_ref.id,
                    'group_of_product': item.group_of_product.id,
                    'overhead_gop_amount_total': item.overhead_amount_total,
                    'actual_used_amt': item.actual_used_amt,
                    'reserved_amt': item.reserved_amt,
                    'allocated_budget_amt': item.allocated_budget_amt,
                    'billed_amt': item.billed_amt,
                    'purchased_amt': item.purchased_amt,
                }

        # This context is used when creating new quotation from wizard
        # Will conflict with this onchange
        if 'default_overhead_line_ids' in self._context:
            self.env.context = dict(self.env.context)
            self.env.context.update({'default_overhead_line_ids': False})

        self.material_overhead_gop_ids = [(0, 0, item) for k, item in gop_budget_dict.items()]

    @api.onchange('material_equipment_ids')
    def get_gop_equipment_table(self):
        self.material_equipment_gop_ids = [(5, 0, 0)]
        gop_budget_dict = {}
        for item in self.material_equipment_ids:
            # key_gop_budget = project_scope + section_name + group_of_product
            key_gop_budget = str(item.project_scope.id) + str(item.section_name.id) + str(item.group_of_product.id)
            if gop_budget_dict.get(key_gop_budget, False):
                gop_budget_dict[key_gop_budget]['equipment_gop_amount_total'] += item.equipment_amount_total
                gop_budget_dict[key_gop_budget]['actual_used_amt'] += item.actual_used_amt
                gop_budget_dict[key_gop_budget]['reserved_amt'] += item.reserved_amt
                gop_budget_dict[key_gop_budget]['allocated_budget_amt'] += item.allocated_budget_amt
                gop_budget_dict[key_gop_budget]['billed_amt'] += item.billed_amt
                gop_budget_dict[key_gop_budget]['purchased_amt'] += item.purchased_amt
            else:
                gop_budget_dict[key_gop_budget] = {
                    'project_scope': item.project_scope.id,
                    'section_name': item.section_name.id,
                    'variable_ref': item.variable_ref.id,
                    'group_of_product': item.group_of_product.id,
                    'equipment_gop_amount_total': item.equipment_amount_total,
                    'actual_used_amt': item.actual_used_amt,
                    'reserved_amt': item.reserved_amt,
                    'allocated_budget_amt': item.allocated_budget_amt,
                    'billed_amt': item.billed_amt,
                    'purchased_amt': item.purchased_amt,
                }

        # This context is used when creating new quotation from wizard
        # Will conflict with this onchange
        if 'default_equipment_line_ids' in self._context:
            self.env.context = dict(self.env.context)
            self.env.context.update({'default_equipment_line_ids': False})

        self.material_equipment_gop_ids = [(0, 0, item) for k, item in gop_budget_dict.items()]

    def send_vo_material(self, material):
        return {
            'project_scope': material.project_scope.id,
            'section_name': material.section_name.id,
            'variable_ref': material.variable_ref.id,
            'group_of_product': material.group_of_product.id,
            'product_id': material.material_id.id,
            'description': material.description,
            'product_qty': material.quantity,
            'uom_id': material.uom_id.id,
            'price_unit': material.unit_price,
            'material_amount_total': material.subtotal,
        }

    def send_vo_labour(self, labour):
        return {
            'project_scope': labour.project_scope.id,
            'section_name': labour.section_name.id,
            'variable_ref': labour.variable_ref.id,
            'group_of_product': labour.group_of_product.id,
            'product_id': labour.labour_id.id,
            'description': labour.description,
            # 'product_qty': labour.quantity,
            'time': labour.time,
            'contractors': labour.contractors,
            'uom_id': labour.uom_id.id,
            'price_unit': labour.unit_price,
            'labour_amount_total': labour.subtotal,
        }

    def send_vo_subcon(self, subcon):
        return {
            'project_scope': subcon.project_scope.id,
            'section_name': subcon.section_name.id,
            'variable_ref': subcon.variable_ref.id,
            'variable': subcon.subcon_id.id,
            'description': subcon.description,
            'product_qty': subcon.quantity,
            'uom_id': subcon.uom_id.id,
            'price_unit': subcon.unit_price,
            'subcon_amount_total': subcon.subtotal,
        }

    def send_vo_overhead(self, overhead):
        return {
            'project_scope': overhead.project_scope.id,
            'section_name': overhead.section_name.id,
            'variable_ref': overhead.variable_ref.id,
            'group_of_product': overhead.group_of_product.id,
            'product_id': overhead.overhead_id.id,
            'description': overhead.description,
            'product_qty': overhead.quantity,
            'uom_id': overhead.uom_id.id,
            'price_unit': overhead.unit_price,
            'overhead_catagory': overhead.overhead_catagory,
            'overhead_amount_total': overhead.subtotal,
        }

    def send_vo_asset(self, asset):
        return {
            'project_scope': asset.project_scope.id,
            'section_name': asset.section_name.id,
            'variable_ref': asset.variable_ref.id,
            'asset_category_id': asset.asset_category_id.id,
            'asset_id': asset.asset_id.id,
            'description': asset.description,
            'budgeted_qty': asset.quantity,
            'uom_id': asset.uom_id.id,
            'price_unit': asset.unit_price,
            'budgeted_amt': asset.subtotal,
        }

    def send_vo_equipment(self, equipment):
        return {
            'project_scope': equipment.project_scope.id,
            'section_name': equipment.section_name.id,
            'variable_ref': equipment.variable_ref.id,
            'group_of_product': equipment.group_of_product.id,
            'product_id': equipment.equipment_id.id,
            'description': equipment.description,
            'product_qty': equipment.quantity,
            'uom_id': equipment.uom_id.id,
            'price_unit': equipment.unit_price,
            'equipment_amount_total': equipment.subtotal,
        }

    def filter_ids(self, exist_ids, line=False, line_product_id=False):
        filtered_ids = exist_ids.filtered(lambda p: p.project_scope.id == line.project_scope.id and
                                                    p.section_name.id == line.section_name.id and
                                                    p.group_of_product.id == line.group_of_product.id and
                                                    p.product_id.id == line_product_id.id and
                                                    p.description == line.description)
        return filtered_ids

    def filter_ids_subcon(self, exist_ids, line=False, line_product_id=False):
        filtered_ids = exist_ids.filtered(lambda p: p.project_scope.id == line.project_scope.id and
                                                    p.section_name.id == line.section_name.id and
                                                    p.variable.id == line_product_id.id and
                                                    p.description == line.description)
        return filtered_ids

    def filter_asset_ids(self, exist_ids, line=False, line_product_id=False):
        filtered_ids = exist_ids.filtered(lambda p: p.project_scope.id == line.project_scope.id and
                                                    p.section_name.id == line.section_name.id and
                                                    p.asset_category_id.id == line.asset_category_id.id and
                                                    p.asset_id.id == line_product_id.id)
        return filtered_ids

    def _variation_order_send(self, sale_id):
        if not self.is_empty_cost_sheet:
            sale = sale_id
            updated_variation_order_history = []
            is_updated_subcon_exist = False
            is_added_subcon_exist = False
            is_removed_subcon_exist = False

            is_updated_asset_exist = False
            is_added_asset_exist = False
            is_removed_asset_exist = False

            for material in sale.material_line_ids:
                exist_ids = self.material_ids
                product_id = material.material_id
                if len(sale.project_budget_ids) == 0:
                    exist_line = material.cs_material_id
                    if exist_line:
                        exist_line.product_qty += material.quantity
                        exist_line.material_amount_total += material.subtotal
                        exist_line.price_unit = material.unit_price
                    else:
                        self.material_ids = [(0, 0, self.send_vo_material(material))]
                elif len(sale.project_budget_ids) > 0:
                    cost_sheet_material = material.cs_material_id
                    if cost_sheet_material:
                        cost_sheet_material.product_qty += material.quantity
                        # cost_sheet_material.material_amount_total += material.subtotal
                        cost_sheet_material.price_unit = material.unit_price
                        cost_sheet_material.allocated_budget_qty += material.quantity
                        cost_sheet_material.allocated_budget_amt += material.quantity * material.unit_price

                    elif material.budget_quantity == 0 and material.quantity_after > 0:
                        self.write({
                            'material_ids': [(0, 0, {
                                'job_sheet_id': sale.cost_sheet_ref.id,
                                'project_scope': material.project_scope.id,
                                'section_name': material.section_name.id,
                                'variable_ref': material.variable_ref.id,
                                'group_of_product': material.group_of_product.id,
                                'product_id': material.material_id.id,
                                'description': material.description,
                                'product_qty': material.quantity,
                                'uom_id': material.uom_id.id,
                                'price_unit': material.unit_price,
                                # 'material_amount_total': material.subtotal,
                                'allocated_budget_qty': material.quantity,
                                'allocated_budget_amt': material.subtotal,
                            })]
                        })

                    for boq_line in material.material_boq_ids:
                        project_budget_material = boq_line.bd_material_id
                        project_budget = boq_line.project_budget_id

                        if cost_sheet_material and project_budget_material:
                            project_budget_material.quantity += boq_line.quantity
                            # project_budget_material.amount_total += material.subtotal
                            project_budget_material.budget_amount += cost_sheet_material.material_amount_total
                            project_budget_material.amount = boq_line.unit_price

                            # Also change other budget with same product unit price
                            if boq_line.budget_unit_price != boq_line.unit_price:
                                project_budget_ids = sale.cost_sheet_ref.periodical_budget_ids.filtered(
                                    lambda r: r.id != boq_line.bd_material_id.budget_id.id)
                                for budget in project_budget_ids:
                                    material_line = budget.budget_material_ids.filtered(
                                        lambda r: r.cs_material_id.id == boq_line.cs_material_id.id)
                                    if material_line:
                                        material_line.amount = boq_line.unit_price
                        elif boq_line.budget_quantity == 0 and boq_line.quantity_after > 0:
                            project_budget.write({
                                'budget_material_ids': [(0, 0, {
                                    'cs_material_id': material.cs_material_id.id,
                                    'project_scope': material.project_scope.id,
                                    'section_name': material.section_name.id,
                                    'variable': material.variable_ref.id,
                                    'group_of_product': material.group_of_product.id,
                                    'product_id': product_id.id,
                                    'description': material.description,
                                    'quantity': boq_line.quantity,
                                    'uom_id': boq_line.uom_id.id,
                                    'budget_quantity': material.quantity,
                                    'amount': boq_line.unit_price,
                                    'budget_amount': material.subtotal,
                                    'unallocated_quantity': 0,
                                    'unallocated_amount': 0,
                                })]
                            })

                if material.budget_quantity == 0 and material.quantity_after > 0:
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_added',
                        'project_scope_id': material.project_scope.id,
                        'section_id': material.section_name.id,
                        'group_of_product_id': material.group_of_product.id,
                        'product_id': material.material_id.id,
                        'quantity_before': material.budget_quantity,
                        'quantity_after': material.quantity_after,
                        'unit_price_before': material.budget_unit_price,
                        'unit_price_after': material.unit_price,
                        'uom_id': material.uom_id.id,
                        'subtotal': material.subtotal,
                    }))
                elif material.budget_quantity > 0 and material.quantity_after == 0:
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_removed',
                        'project_scope_id': material.project_scope.id,
                        'section_id': material.section_name.id,
                        'group_of_product_id': material.group_of_product.id,
                        'product_id': material.material_id.id,
                        'quantity_before': material.budget_quantity,
                        'quantity_after': material.quantity_after,
                        'unit_price_before': material.budget_unit_price,
                        'unit_price_after': material.unit_price,
                        'uom_id': material.uom_id.id,
                        'subtotal': material.subtotal,
                    }))
                elif (material.budget_quantity != material.quantity_after) or (
                        material.budget_unit_price != material.unit_price):
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_updated',
                        'project_scope_id': material.project_scope.id,
                        'section_id': material.section_name.id,
                        'group_of_product_id': material.group_of_product.id,
                        'product_id': material.material_id.id,
                        'quantity_before': material.budget_quantity,
                        'quantity_after': material.quantity_after,
                        'unit_price_before': material.budget_unit_price,
                        'unit_price_after': material.unit_price,
                        'uom_id': material.uom_id.id,
                        'subtotal': material.subtotal,
                    }))

            for labour in sale.labour_line_ids:
                exist_ids = self.material_labour_ids
                product_id = labour.labour_id
                if len(sale.project_budget_ids) == 0:
                    exist_line = labour.cs_labour_id
                    if exist_line:
                        # exist_line.product_qty += labour.quantity
                        exist_line.time += labour.time
                        exist_line.contractors += labour.contractors
                        exist_line.labour_amount_total += labour.subtotal
                        exist_line.price_unit = labour.unit_price
                    else:
                        self.material_labour_ids = [(0, 0, self.send_vo_labour(labour))]
                elif len(sale.project_budget_id) > 0:
                    cost_sheet_labour = labour.cs_labour_id

                    if cost_sheet_labour:
                        cost_sheet_labour.time += labour.time
                        cost_sheet_labour.contractors += labour.contractors
                        # cost_sheet_labour.labour_amount_total += labour.subtotal
                        cost_sheet_labour.price_unit = labour.unit_price
                        cost_sheet_labour.allocated_budget_time += labour.time
                        cost_sheet_labour.allocated_contractors += labour.contractors
                        cost_sheet_labour.allocated_budget_amt += ((labour.cs_labour_id.contractors+labour.contractors)*(labour.cs_labour_id.time+labour.time)*labour.unit_price)-(labour.cs_labour_id.contractors*labour.time*labour.budget_unit_price)
                        # cost_sheet_labour.allocated_budget_amt += labour.subtotal
                    elif (labour.budget_time == 0 and labour.time_after > 0) and (
                            labour.budget_contractors == 0 and labour.contractors_after > 0):
                        self.write({
                            'material_labour_ids': [(0, 0, {
                                'job_sheet_id': sale.cost_sheet_ref.id,
                                'project_scope': labour.project_scope.id,
                                'section_name': labour.section_name.id,
                                'variable_ref': labour.variable_ref.id,
                                'group_of_product': labour.group_of_product.id,
                                'product_id': labour.labour_id.id,
                                'description': labour.description,
                                # 'product_qty': labour.quantity,
                                'time': labour.time,
                                'contractors': labour.contractors,
                                'uom_id': labour.uom_id.id,
                                'price_unit': labour.unit_price,
                                'labour_amount_total': labour.subtotal,
                                # 'allocated_budget_qty': labour.quantity,
                                'allocated_budget_time': labour.time,
                                'allocated_contractors': labour.contractors,
                                'allocated_budget_amt': labour.subtotal,
                            })]
                        })
                    for boq_line in labour.labour_boq_ids:
                        project_budget_labour = boq_line.bd_labour_id
                        project_budget = boq_line.project_budget_id

                        if cost_sheet_labour and project_budget_labour:
                            project_budget_labour.time += boq_line.time
                            project_budget_labour.contractors += boq_line.contractors
                            # project_budget_labour.amount_total += labour.subtotal
                            project_budget_labour.budget_amount += cost_sheet_labour.labour_amount_total
                            project_budget_labour.amount = boq_line.unit_price

                            # Also change other budget with same product unit price
                            if boq_line.budget_unit_price != boq_line.unit_price:
                                project_budget_ids = sale.cost_sheet_ref.periodical_budget_ids.filtered(
                                    lambda r: r.id != boq_line.bd_labour_id.budget_id.id)
                                for budget in project_budget_ids:
                                    labour_line = budget.budget_labour_ids.filtered(
                                        lambda r: r.cs_labour_id.id == boq_line.cs_labour_id.id)
                                    if labour_line:
                                        labour_line.amount = boq_line.unit_price
                        elif (boq_line.budget_time == 0 and boq_line.time_after > 0) and (
                                boq_line.budget_contractors == 0 and boq_line.contractors_after > 0):
                            project_budget.write({
                                'budget_labour_ids': [(0, 0, {
                                    'cs_labour_id': labour.cs_labour_id.id,
                                    'project_scope': labour.project_scope.id,
                                    'section_name': labour.section_name.id,
                                    'variable': labour.variable_ref.id,
                                    'group_of_product': labour.group_of_product.id,
                                    'product_id': product_id.id,
                                    'description': labour.description,
                                    # 'quantity': labour.quantity,
                                    'time': boq_line.time,
                                    'contractors': boq_line.contractors,
                                    'uom_id': labour.uom_id.id,
                                    # 'budget_quantity': labour.quantity,
                                    'amount': boq_line.unit_price,
                                    'budget_amount': labour.subtotal,
                                    # 'unallocated_quantity': 0,
                                    'unallocated_time': 0,
                                    'unallocated_contractors': 0,
                                    'unallocated_amount': 0,
                                })]
                            })

                if (labour.budget_time == 0 and labour.time_after > 0) and (
                        labour.budget_contractors == 0 and labour.contractors_after > 0):
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_added',
                        'project_scope_id': labour.project_scope.id,
                        'section_id': labour.section_name.id,
                        'group_of_product_id': labour.group_of_product.id,
                        'product_id': labour.labour_id.id,
                        'time_before': labour.budget_time,
                        'time_after': labour.time_after,
                        'contractors_before': labour.budget_contractors,
                        'contractors_after': labour.contractors_after,
                        'unit_price_before': labour.budget_unit_price,
                        'unit_price_after': labour.unit_price,
                        'uom_id': labour.uom_id.id,
                        'subtotal': labour.subtotal,
                    }))
                elif (labour.budget_time > 0 and labour.time_after == 0) or (
                        labour.budget_contractors > 0 and labour.contractors_after == 0):
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_removed',
                        'project_scope_id': labour.project_scope.id,
                        'section_id': labour.section_name.id,
                        'group_of_product_id': labour.group_of_product.id,
                        'product_id': labour.labour_id.id,
                        'time_before': labour.budget_time,
                        'time_after': labour.time_after,
                        'contractors_before': labour.budget_contractors,
                        'contractors_after': labour.contractors_after,
                        'unit_price_before': labour.budget_unit_price,
                        'unit_price_after': labour.unit_price,
                        'uom_id': labour.uom_id.id,
                        'subtotal': labour.subtotal,
                    }))
                elif (labour.budget_time != labour.time_after) or (
                        labour.budget_contractors != labour.contractors_after) or (
                        labour.budget_unit_price != labour.unit_price):
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_updated',
                        'project_scope_id': labour.project_scope.id,
                        'section_id': labour.section_name.id,
                        'group_of_product_id': labour.group_of_product.id,
                        'product_id': labour.labour_id.id,
                        'time_before': labour.budget_time,
                        'time_after': labour.time_after,
                        'contractors_before': labour.budget_contractors,
                        'contractors_after': labour.contractors_after,
                        'unit_price_before': labour.budget_unit_price,
                        'unit_price_after': labour.unit_price,
                        'uom_id': labour.uom_id.id,
                        'subtotal': labour.subtotal,
                    }))

            for subcon in sale.subcon_line_ids:
                exist_ids = self.material_subcon_ids
                product_id = subcon.subcon_id
                exist_line = subcon.cs_subcon_id
                if len(sale.project_budget_ids) == 0:
                    if exist_line:
                        exist_line.product_qty += subcon.quantity
                        exist_line.subcon_amount_total += subcon.subtotal
                        exist_line.price_unit = subcon.unit_price
                    else:
                        self.material_subcon_ids = [(0, 0, self.send_vo_subcon(subcon))]
                elif len(sale.project_budget_ids) > 0:
                    cost_sheet_subcon = subcon.cs_subcon_id
                    if cost_sheet_subcon:
                        cost_sheet_subcon.product_qty += subcon.quantity
                        # cost_sheet_subcon.subcon_amount_total += subcon.subtotal
                        cost_sheet_subcon.price_unit = subcon.unit_price
                        cost_sheet_subcon.allocated_budget_qty += subcon.quantity
                        cost_sheet_subcon.allocated_budget_amt += subcon.quantity * subcon.unit_price
                    elif subcon.budget_quantity == 0 and subcon.quantity_after > 0:
                        self.write({
                            'material_subcon_ids': [(0, 0, {
                                'job_sheet_id': sale.cost_sheet_ref.id,
                                'project_scope': subcon.project_scope.id,
                                'section_name': subcon.section_name.id,
                                'variable_ref': subcon.variable_ref.id,
                                # 'group_of_product': subcon.group_of_product.id,
                                'variable': subcon.subcon_id.id,
                                'description': subcon.description,
                                'product_qty': subcon.quantity,
                                'uom_id': subcon.uom_id.id,
                                'price_unit': subcon.unit_price,
                                'subcon_amount_total': subcon.subtotal,
                                'allocated_budget_qty': subcon.quantity,
                                'allocated_budget_amt': subcon.subtotal,
                            })]
                        })
                    for boq_line in subcon.subcon_boq_ids:
                        project_budget_subcon = boq_line.bd_subcon_id
                        project_budget = boq_line.project_budget_id

                        if cost_sheet_subcon and project_budget_subcon:
                            project_budget_subcon.quantity += boq_line.quantity
                            # project_budget_subcon.amount_total += subcon.subtotal
                            project_budget_subcon.budget_amount += cost_sheet_subcon.subcon_amount_total
                            project_budget_subcon.amount = boq_line.unit_price

                            # Also change other budget with same product unit price
                            if boq_line.budget_unit_price != boq_line.unit_price:
                                project_budget_ids = sale.cost_sheet_ref.periodical_budget_ids.filtered(
                                    lambda r: r.id != boq_line.bd_subcon_id.budget_id.id)
                                for budget in project_budget_ids:
                                    subcon_line = budget.budget_subcon_ids.filtered(
                                        lambda r: r.cs_subcon_id.id == boq_line.cs_subcon_id.id)
                                    if subcon_line:
                                        subcon_line.amount = boq_line.unit_price
                        elif boq_line.budget_quantity == 0 and boq_line.quantity_after > 0:
                            project_budget.write({
                                'budget_subcon_ids': [(0, 0, {
                                    'cs_subcon_id': subcon.cs_subcon_id.id,
                                    'project_scope': subcon.project_scope.id,
                                    'section_name': subcon.section_name.id,
                                    # 'variable': subcon.variable_ref.id,
                                    # 'group_of_product': subcon.group_of_product.id,
                                    'subcon_id': product_id.id,
                                    'description': subcon.description,
                                    'quantity': boq_line.quantity,
                                    'uom_id': subcon.uom_id.id,
                                    'budget_quantity': subcon.quantity,
                                    'amount': subcon.unit_price,
                                    'budget_amount': subcon.subtotal,
                                    'unallocated_quantity': 0,
                                    'unallocated_amount': 0,
                                })]
                            })

                if subcon.budget_quantity == 0 and subcon.quantity_after > 0:
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_added',
                        'project_scope_id': subcon.project_scope.id,
                        'section_id': subcon.section_name.id,
                        # 'group_of_product_id': subcon.group_of_product.id,
                        'subcon_id': subcon.subcon_id.id,
                        'quantity_before': subcon.budget_quantity,
                        'quantity_after': subcon.quantity_after,
                        'unit_price_before': subcon.budget_unit_price,
                        'unit_price_after': subcon.unit_price,
                        'uom_id': subcon.uom_id.id,
                        'subtotal': subcon.subtotal,
                    }))
                    is_added_subcon_exist = True
                elif subcon.budget_quantity > 0 and subcon.quantity_after == 0:
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_removed',
                        'project_scope_id': subcon.project_scope.id,
                        'section_id': subcon.section_name.id,
                        # 'group_of_product_id': subcon.group_of_product.id,
                        'subcon_id': subcon.subcon_id.id,
                        'quantity_before': subcon.budget_quantity,
                        'quantity_after': subcon.quantity_after,
                        'unit_price_before': subcon.budget_unit_price,
                        'unit_price_after': subcon.unit_price,
                        'uom_id': subcon.uom_id.id,
                        'subtotal': subcon.subtotal,
                    }))
                    is_added_subcon_exist = True
                elif (subcon.budget_quantity != subcon.quantity_after) or (
                        subcon.budget_unit_price != subcon.unit_price):
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_updated',
                        'project_scope_id': subcon.project_scope.id,
                        'section_id': subcon.section_name.id,
                        # 'group_of_product_id': subcon.group_of_product.id,
                        'subcon_id': subcon.subcon_id.id,
                        'quantity_before': subcon.budget_quantity,
                        'quantity_after': subcon.quantity_after,
                        'unit_price_before': subcon.budget_unit_price,
                        'unit_price_after': subcon.unit_price,
                        'uom_id': subcon.uom_id.id,
                        'subtotal': subcon.subtotal,
                    }))
                    is_updated_subcon_exist = True

            for overhead in sale.overhead_line_ids:
                exist_ids = self.material_overhead_ids
                product_id = overhead.overhead_id
                exist_line = overhead.cs_overhead_id
                if len(sale.project_budget_ids) == 0:
                    if exist_line:
                        exist_line.product_qty += overhead.quantity
                        exist_line.overhead_amount_total += overhead.subtotal
                        exist_line.price_unit = overhead.unit_price
                    else:
                        self.material_overhead_ids = [(0, 0, self.send_vo_overhead(overhead))]

                elif len(sale.project_budget_ids) > 0:
                    cost_sheet_overhead = overhead.cs_overhead_id
                    if cost_sheet_overhead:
                        cost_sheet_overhead.product_qty += overhead.quantity
                        # cost_sheet_overhead.overhead_amount_total += overhead.subtotal
                        cost_sheet_overhead.price_unit = overhead.unit_price
                        cost_sheet_overhead.allocated_budget_qty += overhead.quantity
                        cost_sheet_overhead.allocated_budget_amt += overhead.quantity * overhead.unit_price
                    elif overhead.budget_quantity == 0 and overhead.quantity_after > 0:
                        self.write({
                            'material_overhead_ids': [(0, 0, {
                                'job_sheet_id': sale.cost_sheet_ref.id,
                                'project_scope': overhead.project_scope.id,
                                'section_name': overhead.section_name.id,
                                'variable_ref': overhead.variable_ref.id,
                                'group_of_product': overhead.group_of_product.id,
                                'overhead_catagory': overhead.overhead_catagory,
                                'product_id': overhead.overhead_id.id,
                                'description': overhead.description,
                                'product_qty': overhead.quantity,
                                'uom_id': overhead.uom_id.id,
                                'price_unit': overhead.unit_price,
                                'overhead_amount_total': overhead.subtotal,
                                'allocated_budget_qty': overhead.quantity,
                                'allocated_budget_amt': overhead.subtotal,
                            })]
                        })
                    for boq_line in overhead.overhead_boq_ids:
                        project_budget_overhead = boq_line.bd_overhead_id
                        project_budget = boq_line.project_budget_id

                        if cost_sheet_overhead and project_budget_overhead:
                            project_budget_overhead.quantity += boq_line.quantity
                            # project_budget_overhead.amount_total += overhead.subtotal
                            project_budget_overhead.budget_amount += cost_sheet_overhead.overhead_amount_total
                            project_budget_overhead.amount = boq_line.unit_price

                            # Also change other budget with same product unit price
                            if boq_line.budget_unit_price != boq_line.unit_price:
                                project_budget_ids = sale.cost_sheet_ref.periodical_budget_ids.filtered(
                                    lambda r: r.id != boq_line.bd_overhead_id.budget_id.id)
                                for budget in project_budget_ids:
                                    overhead_line = budget.budget_overhead_ids.filtered(
                                        lambda r: r.cs_overhead_id.id == boq_line.cs_overhead_id.id)
                                    if overhead_line:
                                        overhead_line.amount = boq_line.unit_price
                        elif boq_line.budget_quantity == 0 and boq_line.quantity_after > 0:
                            project_budget.write({
                                'budget_overhead_ids': [(0, 0, {
                                    'cs_overhead_id': overhead.cs_overhead_id.id,
                                    'project_scope': overhead.project_scope.id,
                                    'section_name': overhead.section_name.id,
                                    # 'variable': overhead.variable_ref.id,
                                    'group_of_product': overhead.group_of_product.id,
                                    'overhead_catagory': overhead.overhead_catagory,
                                    'product_id': product_id.id,
                                    'description': overhead.description,
                                    'quantity': boq_line.quantity,
                                    'uom_id': overhead.uom_id.id,
                                    'budget_quantity': overhead.quantity,
                                    'amount': boq_line.unit_price,
                                    'budget_amount': overhead.subtotal,
                                    'unallocated_quantity': 0,
                                    'unallocated_amount': 0,
                                })]
                            })

                if overhead.budget_quantity == 0 and overhead.quantity_after > 0:
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_added',
                        'project_scope_id': overhead.project_scope.id,
                        'section_id': overhead.section_name.id,
                        'group_of_product_id': overhead.group_of_product.id,
                        'product_id': overhead.overhead_id.id,
                        'quantity_before': overhead.budget_quantity,
                        'quantity_after': overhead.quantity_after,
                        'unit_price_before': overhead.budget_unit_price,
                        'unit_price_after': overhead.unit_price,
                        'uom_id': overhead.uom_id.id,
                        'subtotal': overhead.subtotal,
                    }))
                elif overhead.budget_quantity > 0 and overhead.quantity_after == 0:
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_removed',
                        'project_scope_id': overhead.project_scope.id,
                        'section_id': overhead.section_name.id,
                        'group_of_product_id': overhead.group_of_product.id,
                        'product_id': overhead.overhead_id.id,
                        'quantity_before': overhead.budget_quantity,
                        'quantity_after': overhead.quantity_after,
                        'unit_price_before': overhead.budget_unit_price,
                        'unit_price_after': overhead.unit_price,
                        'uom_id': overhead.uom_id.id,
                        'subtotal': overhead.subtotal,
                    }))
                elif (overhead.budget_quantity != overhead.quantity_after) or (
                        overhead.budget_unit_price != overhead.unit_price):
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_updated',
                        'project_scope_id': overhead.project_scope.id,
                        'section_id': overhead.section_name.id,
                        'group_of_product_id': overhead.group_of_product.id,
                        'product_id': overhead.overhead_id.id,
                        'quantity_before': overhead.budget_quantity,
                        'quantity_after': overhead.quantity_after,
                        'unit_price_before': overhead.budget_unit_price,
                        'unit_price_after': overhead.unit_price,
                        'uom_id': overhead.uom_id.id,
                        'subtotal': overhead.subtotal,
                    }))

            for internal_asset in sale.internal_asset_line_ids:
                exist_ids = self.internal_asset_ids
                product_id = internal_asset.asset_id
                exist_line = internal_asset.cs_internal_asset_id
                if len(sale.project_budget_ids) == 0:
                    if exist_line:
                        exist_line.budgeted_qty += internal_asset.quantity
                        exist_line.budgeted_amt += internal_asset.subtotal
                        exist_line.price_unit = internal_asset.unit_price
                    else:
                        self.internal_asset_ids = [(0, 0, self.send_vo_asset(internal_asset))]
                elif len(sale.project_budget_ids) > 0:
                    cost_sheet_internal_asset = internal_asset.cs_internal_asset_id
                    if cost_sheet_internal_asset:
                        cost_sheet_internal_asset.budgeted_qty += internal_asset.quantity
                        # cost_sheet_internal_asset.budgeted_amt += internal_asset.subtotal
                        cost_sheet_internal_asset.price_unit = internal_asset.unit_price
                        cost_sheet_internal_asset.allocated_budget_qty += internal_asset.quantity
                        cost_sheet_internal_asset.allocated_budget_amt += internal_asset.quantity * internal_asset.unit_price
                    elif internal_asset.budget_quantity == 0 and internal_asset.quantity_after > 0:
                        self.write({
                            'internal_asset_ids': [(0, 0, {
                                'job_sheet_id': sale.cost_sheet_ref.id,
                                'project_scope': internal_asset.project_scope.id,
                                'section_name': internal_asset.section_name.id,
                                'variable_ref': internal_asset.variable_ref.id,
                                'asset_category_id': internal_asset.asset_category_id.id,
                                'asset_id': product_id.id,
                                'description': internal_asset.description,
                                'budgeted_qty': internal_asset.quantity,
                                'uom_id': internal_asset.uom_id.id,
                                'price_unit': internal_asset.unit_price,
                                'budgeted_amt': internal_asset.subtotal,
                                'allocated_budget_qty': internal_asset.quantity,
                                'allocated_budget_amt': internal_asset.subtotal,
                            })]
                        })

                    for boq_line in internal_asset.internal_asset_boq_ids:
                        project_budget_internal_asset = boq_line.bd_internal_asset_id
                        project_budget = boq_line.project_budget_id

                        if cost_sheet_internal_asset and project_budget_internal_asset:
                            project_budget_internal_asset.budgeted_qty += boq_line.quantity
                            # project_budget_internal_asset.budgeted_amt += internal_asset.subtotal
                            # project_budget_internal_asset.s += internal_asset.subtotal
                            project_budget_internal_asset.price_unit = boq_line.unit_price

                            # Also change other budget with same product unit price
                            if boq_line.budget_unit_price != boq_line.unit_price:
                                project_budget_ids = sale.cost_sheet_ref.periodical_budget_ids.filtered(
                                    lambda r: r.id != boq_line.bd_internal_asset_id.project_budget_id.id)
                                for budget in project_budget_ids:
                                    internal_asset_line = budget.budget_internal_asset_ids.filtered(
                                        lambda r: r.cs_internal_asset_id.id == boq_line.cs_internal_asset_id.id)
                                    if internal_asset_line:
                                        internal_asset_line.amount = boq_line.unit_price
                        elif internal_asset.budget_quantity == 0 and internal_asset.quantity_after > 0:
                            project_budget.write({
                                'budget_internal_asset_ids': [(0, 0, {
                                    'cs_internal_asset_id': internal_asset.cs_internal_asset_id.id,
                                    'project_scope_line_id': internal_asset.project_scope.id,
                                    'section_name': internal_asset.section_name.id,
                                    # 'variable_ref': internal_asset.variable_ref.id,
                                    'asset_category_id': internal_asset.asset_category_id.id,
                                    'asset_id': product_id.id,
                                    # 'description': internal_asset.description,
                                    'budgeted_qty': boq_line.quantity,
                                    'uom_id': internal_asset.uom_id.id,
                                    # 'budget_quantity': internal_asset.quantity,
                                    'price_unit': boq_line.unit_price,
                                    'budgeted_amt': internal_asset.subtotal,
                                    'unallocated_budget_amt': 0,
                                    'unallocated_budget_qty': 0,
                                })]
                            })

                if internal_asset.budget_quantity == 0 and internal_asset.quantity_after > 0:
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_added',
                        'project_scope_id': internal_asset.project_scope.id,
                        'section_id': internal_asset.section_name.id,
                        # 'group_of_product_id': internal_asset.group_of_product.id,
                        'asset_id': internal_asset.asset_id.id,
                        'quantity_before': internal_asset.budget_quantity,
                        'quantity_after': internal_asset.quantity_after,
                        'unit_price_before': internal_asset.budget_unit_price,
                        'unit_price_after': internal_asset.unit_price,
                        'uom_id': internal_asset.uom_id.id,
                        'subtotal': internal_asset.subtotal,
                    }))
                    is_added_asset_exist = True
                elif internal_asset.budget_quantity > 0 and internal_asset.quantity_after == 0:
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_removed',
                        'project_scope_id': internal_asset.project_scope.id,
                        'section_id': internal_asset.section_name.id,
                        # 'group_of_product_id': internal_asset.group_of_product.id,
                        'asset_id': internal_asset.asset_id.id,
                        'quantity_before': internal_asset.budget_quantity,
                        'quantity_after': internal_asset.quantity_after,
                        'unit_price_before': internal_asset.budget_unit_price,
                        'unit_price_after': internal_asset.unit_price,
                        'uom_id': internal_asset.uom_id.id,
                        'subtotal': internal_asset.subtotal,
                    }))
                    is_removed_asset_exist = True
                elif (internal_asset.budget_quantity != internal_asset.quantity_after) or (internal_asset.budget_unit_price != internal_asset.unit_price):
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_updated',
                        'project_scope_id': internal_asset.project_scope.id,
                        'section_id': internal_asset.section_name.id,
                        # 'group_of_product_id': internal_asset.group_of_product.id,
                        'asset_id': internal_asset.asset_id.id,
                        'quantity_before': internal_asset.budget_quantity,
                        'quantity_after': internal_asset.quantity_after,
                        'unit_price_before': internal_asset.budget_unit_price,
                        'unit_price_after': internal_asset.unit_price,
                        'uom_id': internal_asset.uom_id.id,
                        'subtotal': internal_asset.subtotal,
                    }))
                    is_updated_asset_exist = True

            for equipment in sale.equipment_line_ids:
                exist_ids = self.material_equipment_ids
                product_id = equipment.equipment_id
                exist_line = equipment.cs_equipment_id
                if len(sale.project_budget_ids) == 0:
                    if exist_line:
                        exist_line.product_qty += equipment.quantity
                        exist_line.equipment_amount_total += equipment.subtotal
                        exist_line.price_unit = equipment.unit_price
                    else:
                        self.material_equipment_ids = [(0, 0, self.send_vo_equipment(equipment))]
                elif len(sale.project_budget_ids) > 0:
                    cost_sheet_equipment = equipment.cs_equipment_id
                    if cost_sheet_equipment:
                        cost_sheet_equipment.product_qty += equipment.quantity
                        # cost_sheet_equipment.equipment_amount_total += equipment.subtotal
                        cost_sheet_equipment.price_unit = equipment.unit_price
                        cost_sheet_equipment.allocated_budget_qty += equipment.quantity
                        cost_sheet_equipment.allocated_budget_amt += equipment.quantity * equipment.unit_price
                    elif equipment.budget_quantity == 0 and equipment.quantity_after > 0:
                        self.write({
                            'material_equipment_ids': [(0, 0, {
                                'job_sheet_id': sale.cost_sheet_ref.id,
                                'project_scope': equipment.project_scope.id,
                                'section_name': equipment.section_name.id,
                                'variable_ref': equipment.variable_ref.id,
                                'group_of_product': equipment.group_of_product.id,
                                'product_id': equipment.equipment_id.id,
                                'description': equipment.description,
                                'product_qty': equipment.quantity,
                                'uom_id': equipment.uom_id.id,
                                'price_unit': equipment.unit_price,
                                'equipment_amount_total': equipment.subtotal,
                                'allocated_budget_qty': equipment.quantity,
                                'allocated_budget_amt': equipment.subtotal,
                            })]
                        })
                    for boq_line in equipment.equipment_boq_ids:
                        project_budget_equipment = boq_line.bd_equipment_id
                        project_budget = boq_line.project_budget_id

                        if cost_sheet_equipment and project_budget_equipment:
                            project_budget_equipment.quantity += boq_line.quantity
                            # project_budget_equipment.amount_total += equipment.subtotal
                            project_budget_equipment.budget_amount += cost_sheet_equipment.equipment_amount_total
                            project_budget_equipment.amount = boq_line.unit_price

                            # Also change other budget with same product unit price
                            if boq_line.budget_unit_price != boq_line.unit_price:
                                project_budget_ids = sale.cost_sheet_ref.periodical_budget_ids.filtered(
                                    lambda r: r.id != boq_line.bd_equipment_id.budget_id.id)
                                for budget in project_budget_ids:
                                    equipment_line = budget.budget_equipment_ids.filtered(
                                        lambda r: r.cs_equipment_id.id == boq_line.cs_equipment_id.id)
                                    if equipment_line:
                                        equipment_line.amount = boq_line.unit_price
                        elif boq_line.budget_quantity == 0 and boq_line.quantity_after > 0:
                            project_budget.write({
                                'budget_equipment_ids': [(0, 0, {
                                    'cs_equipment_id': equipment.cs_equipment_id.id,
                                    'project_scope': equipment.project_scope.id,
                                    'section_name': equipment.section_name.id,
                                    # 'variable': equipment.variable_ref.id,
                                    'group_of_product': equipment.group_of_product.id,
                                    'product_id': product_id.id,
                                    'description': equipment.description,
                                    'quantity': boq_line.quantity,
                                    'uom_id': equipment.uom_id.id,
                                    'budget_quantity': equipment.quantity,
                                    'amount': boq_line.unit_price,
                                    'budget_amount': equipment.subtotal,
                                    'unallocated_quantity': 0,
                                    'unallocated_amount': 0,
                                })]
                            })

                if equipment.budget_quantity == 0 and equipment.quantity_after > 0:
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_added',
                        'project_scope_id': equipment.project_scope.id,
                        'section_id': equipment.section_name.id,
                        'group_of_product_id': equipment.group_of_product.id,
                        'product_id': equipment.equipment_id.id,
                        'quantity_before': equipment.budget_quantity,
                        'quantity_after': equipment.quantity_after,
                        'unit_price_before': equipment.budget_unit_price,
                        'unit_price_after': equipment.unit_price,
                        'uom_id': equipment.uom_id.id,
                        'subtotal': equipment.subtotal,
                    }))
                elif equipment.budget_quantity > 0 and equipment.quantity_after == 0:
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_removed',
                        'project_scope_id': equipment.project_scope.id,
                        'section_id': equipment.section_name.id,
                        'group_of_product_id': equipment.group_of_product.id,
                        'product_id': equipment.equipment_id.id,
                        'quantity_before': equipment.budget_quantity,
                        'quantity_after': equipment.quantity_after,
                        'unit_price_before': equipment.budget_unit_price,
                        'unit_price_after': equipment.unit_price,
                        'uom_id': equipment.uom_id.id,
                        'subtotal': equipment.subtotal,
                    }))
                elif (equipment.budget_quantity != equipment.quantity_after) or (
                        equipment.budget_unit_price != equipment.unit_price):
                    updated_variation_order_history.append((0, 0, {
                        'history_category': 'is_updated',
                        'project_scope_id': equipment.project_scope.id,
                        'section_id': equipment.section_name.id,
                        'group_of_product_id': equipment.group_of_product.id,
                        'product_id': equipment.equipment_id.id,
                        'quantity_before': equipment.budget_quantity,
                        'quantity_after': equipment.quantity_after,
                        'unit_price_before': equipment.budget_unit_price,
                        'unit_price_after': equipment.unit_price,
                        'uom_id': equipment.uom_id.id,
                        'subtotal': equipment.subtotal,
                    }))

            self.contract_history_ids = [(0, 0, {
                'contract_history': sale.id,
                'contract_category': sale.contract_category,
                'job_reference': [(6, 0, [v.id for v in sale.job_references])],
                'date_order': sale.date_order,
                'subtotal': sale.amount_untaxed,
                'created_by': sale.create_uid.id,
                'state': 'in_progress',
                'updated_variation_order_history_ids': updated_variation_order_history,
                #only update one field since two other fields using same model
                'is_updated_subcon_exist': is_updated_subcon_exist,
                'is_added_subcon_exist': is_added_subcon_exist,
                'is_removed_subcon_exist': is_removed_subcon_exist,
                'is_updated_asset_exist': is_updated_asset_exist,
                'is_added_asset_exist': is_added_asset_exist,
                'is_removed_asset_exist': is_removed_asset_exist,
            })]

            self.set_scope_section_table()
            if self.budgeting_method == 'gop_budget':
                self.get_gop_material_table()
                self.get_gop_labour_table()
                self.get_gop_overhead_table()
                self.get_gop_equipment_table()

                if len(sale.project_budget_id) > 0:
                    sale.project_budget_id.get_gop_material_table()
                    sale.project_budget_id.get_gop_labour_table()
                    sale.project_budget_id.get_gop_overhead_table()
                    sale.project_budget_id.get_gop_equipment_table()

    def _onchange_sale_order_ref(self):
        self.contract_history_ids = [(5, 0, 0)]
        self.material_ids = [(5, 0, 0)]
        self.material_labour_ids = [(5, 0, 0)]
        self.material_subcon_ids = [(5, 0, 0)]
        self.material_overhead_ids = [(5, 0, 0)]
        self.material_equipment_ids = [(5, 0, 0)]
        self.internal_asset_ids = [(5, 0, 0)]
        for res in self.sale_order_ref:
            self.contract_history_ids = [(0, 0, {
                'contract_history': res._origin.id,
                'contract_category': res.contract_category,
                'job_reference': [(6, 0, [v.id for v in res.job_references])],
                'date_order': res.date_order,
                'subtotal': res.amount_untaxed,
                'created_by': res.create_uid.id,
                'state': 'in_progress',
            })]

        self._sales_order_onchange()
        self.set_scope_section_table()
        self.get_gop_material_table()
        self.get_gop_labour_table()
        self.get_gop_overhead_table()
        self.get_gop_equipment_table()

    def _onchange_sale_order_ref_empty_cost_sheet(self):
        self.contract_history_ids = [(5, 0, 0)]
        self.material_ids = [(5, 0, 0)]
        self.material_labour_ids = [(5, 0, 0)]
        self.material_subcon_ids = [(5, 0, 0)]
        self.material_overhead_ids = [(5, 0, 0)]
        self.material_equipment_ids = [(5, 0, 0)]
        self.internal_asset_ids = [(5, 0, 0)]
        for res in self.sale_order_ref:
            self.contract_history_ids = [(0, 0, {
                'contract_history': res._origin.id,
                'contract_category': res.contract_category,
                'job_reference': [(6, 0, [v.id for v in res.job_references])],
                'date_order': res.date_order,
                'subtotal': res.amount_untaxed,
                'created_by': res.create_uid.id,
                'state': 'in_progress',
            })]
        self.set_scope_section_table()

    def _onchange_job_reference(self):
        for rec in self:
            rec.contract_history_ids = [(5, 0, 0)]
            rec.project_scope_cost_ids = [(5, 0, 0)]
            rec.section_cost_ids = [(5, 0, 0)]
            rec.material_ids = [(5, 0, 0)]
            rec.material_labour_ids = [(5, 0, 0)]
            rec.material_subcon_ids = [(5, 0, 0)]
            rec.material_overhead_ids = [(5, 0, 0)]
            rec.material_equipment_ids = [(5, 0, 0)]
            rec.internal_asset_ids = [(5, 0, 0)]
            for res in rec.job_reference:
                rec.contract_history_ids = [(0, 0, {
                    'contract_category': res.contract_category,
                    'job_estimate': res._origin.id,
                    'approved_date': datetime.now(),
                    'subtotal': res.total_job_estimate,
                    'created_by': res.create_uid.id,
                    'state': 'in_progress',
                })]

            rec._onchange_job_estimate()

    def _onchange_job_estimate(self):
        if self.job_reference:
            sale = self.job_reference
            data_added = []
            gop_added = []

            for material in sale.material_estimation_ids:
                append = True
                append2 = True
                section_new_data = self.env['section.line'].search([('id', '=', material.section_name.id)])
                scope_new_data = self.env['project.scope.line'].search([('id', '=', material.project_scope.id)])
                for data in data_added:
                    scope_data = self.env['project.scope.line'].search([('id', '=', data[2].get('project_scope'))])
                    section_data = self.env['section.line'].search([('id', '=', data[2].get('section_name'))])
                    condition = [
                        scope_new_data.id == scope_data.id,
                        section_new_data.id == section_data.id,
                        data[2].get('group_of_product') == material.group_of_product.id,
                        data[2].get('product_id') == material.product_id.id,
                        data[2].get('description') == material.description,
                        data[2].get('uom_id') == material.uom_id.id,
                    ]
                    if all(condition):
                        append = False
                        data[2]['product_qty'] += material.quantity
                        data[2]['material_amount_total'] += material.subtotal
                for data in gop_added:
                    scope_data = self.env['project.scope.line'].search([('id', '=', data[2].get('project_scope'))])
                    section_data = self.env['section.line'].search([('id', '=', data[2].get('section_name'))])
                    condition2 = [
                        scope_new_data.id == scope_data.id,
                        section_new_data.id == section_data.id,
                        data[2].get('group_of_product') == material.group_of_product.id
                    ]
                    if all(condition2):
                        append2 = False
                        data[2]['material_gop_amount_total'] += material.subtotal
                if append:
                    data_added.append((0, 0, {
                        'project_scope': material.project_scope.id,
                        'section_name': material.section_name.id,
                        'variable_ref': material.variable_ref.id,
                        'group_of_product': material.group_of_product.id,
                        'product_id': material.product_id.id,
                        'description': material.description,
                        'product_qty': material.quantity,
                        'uom_id': material.uom_id.id,
                        'price_unit': material.unit_price,
                        'material_amount_total': material.subtotal,
                    }))
                if append2:
                    gop_added.append((0, 0, {
                        'project_scope': material.project_scope.id,
                        'section_name': material.section_name.id,
                        'variable_ref': material.variable_ref.id,
                        'group_of_product': material.group_of_product.id,
                        'material_gop_amount_total': material.subtotal,
                    }))
            self.material_ids = data_added
            self.material_gop_ids = gop_added

            data_added = []
            gop_added = []
            for labour in sale.labour_estimation_ids:
                append = True
                append2 = True
                section_new_data = self.env['section.line'].search([('id', '=', labour.section_name.id)])
                scope_new_data = self.env['project.scope.line'].search([('id', '=', labour.project_scope.id)])
                for data in data_added:
                    scope_data = self.env['project.scope.line'].search([('id', '=', data[2].get('project_scope'))])
                    section_data = self.env['section.line'].search([('id', '=', data[2].get('section_name'))])
                    condition = [
                        scope_new_data.id == scope_data.id,
                        section_new_data.id == section_data.id,
                        data[2].get('group_of_product') == labour.group_of_product.id,
                        data[2].get('product_id') == labour.product_id.id,
                        data[2].get('description') == labour.description,
                        data[2].get('uom_id') == labour.uom_id.id,
                    ]
                    if all(condition):
                        append = False
                        data[2]['time'] += labour.time
                        data[2]['contractors'] += labour.contractors
                        data[2]['product_qty'] += labour.quantity
                        data[2]['labour_amount_total'] += labour.subtotal
                for data in gop_added:
                    condition2 = [
                        scope_new_data.id == scope_data.id,
                        section_new_data.id == section_data.id,
                        data[2].get('group_of_product') == labour.group_of_product.id
                    ]
                    if all(condition2):
                        append2 = False
                        data[2]['labour_gop_amount_total'] += labour.subtotal
                if append:
                    data_added.append((0, 0, {
                        'project_scope': labour.project_scope.id,
                        'section_name': labour.section_name.id,
                        'variable_ref': labour.variable_ref.id,
                        'group_of_product': labour.group_of_product.id,
                        'product_id': labour.product_id.id,
                        'description': labour.description,
                        'product_qty': labour.quantity,
                        'time': labour.time,
                        'contractors': labour.contractors,
                        'uom_id': labour.uom_id.id,
                        'price_unit': labour.unit_price,
                        'labour_amount_total': labour.subtotal,
                    }))
                if append2:
                    gop_added.append((0, 0, {
                        'project_scope': labour.project_scope.id,
                        'section_name': labour.section_name.id,
                        'variable_ref': labour.variable_ref.id,
                        'group_of_product': labour.group_of_product.id,
                        'labour_gop_amount_total': labour.subtotal,
                    }))
            self.material_labour_ids = data_added
            self.material_labour_gop_ids = gop_added

            data_added = []
            gop_added = []
            for subcon in sale.subcon_estimation_ids:
                append = True
                append2 = True
                section_new_data = self.env['section.line'].search([('id', '=', subcon.section_name.id)])
                scope_new_data = self.env['project.scope.line'].search([('id', '=', subcon.project_scope.id)])
                for data in data_added:
                    scope_data = self.env['project.scope.line'].search([('id', '=', data[2].get('project_scope'))])
                    section_data = self.env['section.line'].search([('id', '=', data[2].get('section_name'))])
                    condition = [
                        scope_new_data.id == scope_data.id,
                        section_new_data.id == section_data.id,
                        data[2].get('variable') == subcon.variable.id,
                        data[2].get('description') == subcon.description,
                        data[2].get('uom_id') == subcon.uom_id.id,
                    ]
                    if all(condition):
                        append = False
                        data[2]['product_qty'] += subcon.quantity
                        data[2]['subcon_amount_total'] += subcon.subtotal
                # for data in gop_added:
                #     condition2 = [
                #         scope_new_data.name == scope_data.name,
                #         section_new_data.name == section_data.name,
                #         data[2].get('group_of_product') == subcon.group_of_product.id
                #     ]
                #     if all(condition2):
                #         append2 = False
                #         data[2]['subcon_gop_amount_total'] += subcon.subtotal
                if append:
                    data_added.append((0, 0, {
                        'project_scope': subcon.project_scope.id,
                        'section_name': subcon.section_name.id,
                        'variable_ref': subcon.variable_ref.id,
                        'variable': subcon.variable.id,
                        'description': subcon.description,
                        'product_qty': subcon.quantity,
                        'uom_id': subcon.uom_id.id,
                        'price_unit': subcon.unit_price,
                        'subcon_amount_total': subcon.subtotal,
                    }))
                # if append2:
                #     gop_added.append((0, 0, {
                #         'project_scope': subcon.project_scope.id,
                #         'section_name': subcon.section_name.id,
                #         'variable_ref': subcon.variable_ref.id,
                #         'group_of_product': subcon.group_of_product.id,
                #         'subcon_gop_amount_total': subcon.subtotal,
                #     }))
            self.material_subcon_ids = data_added
            # self.material_subcon_gop_ids = gop_added

            data_added = []
            gop_added = []
            for overhead in sale.overhead_estimation_ids:
                append = True
                append2 = True
                section_data = self.env['section.line'].search([('id', '=', overhead.section_name.id)])
                scope_data = self.env['project.scope.line'].search([('id', '=', overhead.project_scope.id)])
                for data in data_added:
                    scope_new_data = self.env['project.scope.line'].search([('id', '=', data[2].get('project_scope'))])
                    section_new_data = self.env['section.line'].search([('id', '=', data[2].get('section_name'))])
                    condition = [
                        scope_new_data.id == scope_data.id,
                        section_new_data.id == section_data.id,
                        data[2].get('overhead_catagory') == overhead.overhead_catagory,
                        data[2].get('group_of_product') == overhead.group_of_product.id,
                        data[2].get('product_id') == overhead.product_id.id,
                        data[2].get('description') == overhead.description,
                        data[2].get('uom_id') == overhead.uom_id.id,
                    ]
                    if all(condition):
                        append = False
                        data[2]['product_qty'] += overhead.quantity
                        data[2]['overhead_amount_total'] += overhead.subtotal
                for data in gop_added:
                    condition2 = [
                        scope_new_data.id == scope_data.id,
                        section_new_data.id == section_data.id,
                        data[2].get('group_of_product') == overhead.group_of_product.id
                    ]
                    if all(condition2):
                        append2 = False
                        data[2]['overhead_gop_amount_total'] += overhead.subtotal
                if append:
                    data_added.append((0, 0, {
                        'project_scope': overhead.project_scope.id,
                        'section_name': overhead.section_name.id,
                        'variable_ref': overhead.variable_ref.id,
                        'overhead_catagory': overhead.overhead_catagory,
                        'group_of_product': overhead.group_of_product.id,
                        'product_id': overhead.product_id.id,
                        'description': overhead.description,
                        'product_qty': overhead.quantity,
                        'uom_id': overhead.uom_id.id,
                        'price_unit': overhead.unit_price,
                        'overhead_amount_total': overhead.subtotal,
                    }))
                if append2:
                    gop_added.append((0, 0, {
                        'project_scope': overhead.project_scope.id,
                        'section_name': overhead.section_name.id,
                        'variable_ref': overhead.variable_ref.id,
                        'group_of_product': overhead.group_of_product.id,
                        'overhead_gop_amount_total': overhead.subtotal,
                    }))
            self.material_overhead_ids = data_added
            self.material_overhead_gop_ids = gop_added

            data_added = []
            for asset in sale.internal_asset_ids:
                append = True
                section_new_data = self.env['section.line'].search([('id', '=', asset.section_name.id)])
                scope_new_data = self.env['project.scope.line'].search([('id', '=', asset.project_scope.id)])
                for data in data_added:
                    scope_data = self.env['project.scope.line'].search([('id', '=', data[2].get('project_scope'))])
                    section_data = self.env['section.line'].search([('id', '=', data[2].get('section_name'))])
                    condition = [
                        scope_new_data.id == scope_data.id,
                        section_new_data.id == section_data.id,
                        data[2].get('asset_category_id') == asset.asset_category_id.id,
                        data[2].get('asset_id') == asset.asset_id.id,
                        data[2].get('description') == asset.description,
                        data[2].get('uom_id') == asset.uom_id.id,
                    ]
                    if all(condition):
                        append = False
                        data[2]['budgeted_qty'] += asset.quantity
                        data[2]['budgeted_amt'] += asset.subtotal

                if append:
                    data_added.append((0, 0, {
                        'project_scope': asset.project_scope.id,
                        'section_name': asset.section_name.id,
                        'variable_ref': asset.variable_ref.id,
                        'asset_category_id': asset.asset_category_id.id,
                        'asset_id': asset.asset_id.id,
                        'description': asset.description,
                        'budgeted_qty': asset.quantity,
                        'uom_id': asset.uom_id.id,
                        'price_unit': asset.unit_price,
                        'budgeted_amt': asset.subtotal,
                    }))
            self.internal_asset_ids = data_added

            data_added = []
            gop_added = []
            for equipment in sale.equipment_estimation_ids:
                append = True
                append2 = True
                section_data = self.env['section.line'].search([('id', '=', equipment.section_name.id)])
                scope_data = self.env['project.scope.line'].search([('id', '=', equipment.project_scope.id)])
                for data in data_added:
                    scope_new_data = self.env['project.scope.line'].search([('id', '=', data[2].get('project_scope'))])
                    section_new_data = self.env['section.line'].search([('id', '=', data[2].get('section_name'))])
                    condition = [
                        scope_new_data.id == scope_data.id,
                        section_new_data.id == section_data.id,
                        data[2].get('group_of_product') == equipment.group_of_product.id,
                        data[2].get('product_id') == equipment.product_id.id,
                        data[2].get('description') == equipment.description,
                        data[2].get('uom_id') == equipment.uom_id.id,
                    ]
                    if all(condition):
                        append = False
                        data[2]['product_qty'] += equipment.quantity
                        data[2]['equipment_amount_total'] += equipment.subtotal
                for data in gop_added:
                    condition2 = [
                        scope_new_data.id == scope_data.id,
                        section_new_data.id == section_data.id,
                        data[2].get('group_of_product') == equipment.group_of_product.id
                    ]
                    if all(condition2):
                        append2 = False
                        data[2]['equipment_gop_amount_total'] += equipment.subtotal
                if append:
                    data_added.append((0, 0, {
                        'project_scope': equipment.project_scope.id,
                        'section_name': equipment.section_name.id,
                        'variable_ref': equipment.variable_ref.id,
                        'group_of_product': equipment.group_of_product.id,
                        'product_id': equipment.product_id.id,
                        'description': equipment.description,
                        'product_qty': equipment.quantity,
                        'uom_id': equipment.uom_id.id,
                        'price_unit': equipment.unit_price,
                        'equipment_amount_total': equipment.subtotal,
                    }))
                if append2:
                    gop_added.append((0, 0, {
                        'project_scope': equipment.project_scope.id,
                        'section_name': equipment.section_name.id,
                        'variable_ref': equipment.variable_ref.id,
                        'group_of_product': equipment.group_of_product.id,
                        'equipment_gop_amount_total': equipment.subtotal,
                    }))
            self.material_equipment_ids = data_added
            self.material_equipment_gop_ids = gop_added

    def _variation_order_job(self, job_id):
        sale = self.env['job.estimate'].search([('id', '=', job_id)])
        for material in sale.material_estimation_ids:
            exist_line = self.material_ids.filtered(lambda p: p.project_scope.name == material.project_scope.name and
                                                              p.section_name.name == material.section_name.name and
                                                              p.group_of_product == material.group_of_product and
                                                              p.product_id == material.product_id and
                                                              p.description == material.description)
            if exist_line:
                exist_line.product_qty += material.quantity
                exist_line.material_amount_total += material.subtotal
            else:
                self.material_ids = [(0, 0, {
                    'project_scope': material.project_scope.id,
                    'section_name': material.section_name.id,
                    'variable_ref': material.variable_ref.id,
                    'group_of_product': material.group_of_product.id,
                    'product_id': material.product_id.id,
                    'description': material.description,
                    'product_qty': material.quantity,
                    'uom_id': material.uom_id.id,
                    'price_unit': material.unit_price,
                    'material_amount_total': material.subtotal,
                })]

        for labour in sale.labour_estimation_ids:
            exist_line = self.material_labour_ids.filtered(
                lambda p: p.project_scope.name == labour.project_scope.name and
                          p.section_name.name == labour.section_name.name and
                          p.group_of_product == labour.group_of_product and
                          p.product_id == labour.product_id and
                          p.description == labour.description)
            if exist_line:
                exist_line.product_qty += labour.quantity
                exist_line.labour_amount_total += labour.subtotal
            else:
                self.material_labour_ids = [(0, 0, {
                    'project_scope': labour.project_scope.id,
                    'section_name': labour.section_name.id,
                    'variable_ref': labour.variable_ref.id,
                    'group_of_product': labour.group_of_product.id,
                    'product_id': labour.product_id.id,
                    'description': labour.description,
                    'product_qty': labour.quantity,
                    'uom_id': labour.uom_id.id,
                    'price_unit': labour.unit_price,
                    'labour_amount_total': labour.subtotal,
                })]

        for subcon in sale.subcon_estimation_ids:
            exist_line = self.material_subcon_ids.filtered(
                lambda p: p.project_scope.name == subcon.project_scope.name and
                          p.section_name.name == subcon.section_name.name and
                          p.variable == subcon.variable.id and
                          p.description == subcon.description)
            if exist_line:
                exist_line.product_qty += subcon.quantity
                exist_line.subcon_amount_total += subcon.subtotal
            else:
                self.material_subcon_ids = [(0, 0, {
                    'project_scope': subcon.project_scope.id,
                    'section_name': subcon.section_name.id,
                    'variable_ref': subcon.variable_ref.id,
                    'variable': subcon.variable.id,
                    'description': subcon.description,
                    'product_qty': subcon.quantity,
                    'uom_id': subcon.uom_id.id,
                    'price_unit': subcon.unit_price,
                    'subcon_amount_total': subcon.subtotal,
                })]

        for overhead in sale.overhead_estimation_ids:
            exist_line = self.material_overhead_ids.filtered(
                lambda p: p.project_scope.name == overhead.project_scope.name and
                          p.section_name.name == overhead.section_name.name and
                          p.overhead_catagory == overhead.overhead_catagory and
                          p.group_of_product == overhead.group_of_product and
                          p.product_id == overhead.product_id and
                          p.description == overhead.description)
            if exist_line:
                exist_line.product_qty += overhead.quantity
                exist_line.overhead_amount_total += overhead.subtotal
            else:
                self.material_overhead_ids = [(0, 0, {
                    'project_scope': overhead.project_scope.id,
                    'section_name': overhead.section_name.id,
                    'variable_ref': overhead.variable_ref.id,
                    'overhead_catagory': overhead.overhead_catagory,
                    'group_of_product': overhead.group_of_product.id,
                    'product_id': overhead.product_id.id,
                    'description': overhead.description,
                    'product_qty': overhead.quantity,
                    'uom_id': overhead.uom_id.id,
                    'price_unit': overhead.unit_price,
                    'overhead_amount_total': overhead.subtotal,
                })]

        for asset in sale.internal_asset_ids:
            exist_line = self.internal_asset_ids.filtered(lambda p: p.project_scope.name == asset.project_scope.name and
                                                                    p.section_name.name == asset.section_name.name and
                                                                    p.asset_category_id == asset.asset_category_id and
                                                                    p.asset_id == asset.asset_id)
            if exist_line:
                exist_line.budgeted_qty += asset.quantity
                exist_line.budgeted_amt += asset.subtotal
            else:
                self.internal_asset_ids = [(0, 0, {
                    'project_scope': asset.project_scope.id,
                    'section_name': asset.section_name.id,
                    'variable_ref': asset.variable_ref.id,
                    'asset_category_id': asset.asset_category_id.id,
                    'asset_id': asset.asset_id.id,
                    'description': asset.description,
                    'budgeted_qty': asset.quantity,
                    'uom_id': asset.uom_id.id,
                    'price_unit': asset.unit_price,
                    'budgeted_amt': asset.subtotal,
                })]

        for equipment in sale.equipment_estimation_ids:
            exist_line = self.material_equipment_ids.filtered(
                lambda p: p.project_scope.name == equipment.project_scope.name and
                          p.section_name.name == equipment.section_name.name and
                          p.group_of_product == equipment.group_of_product and
                          p.product_id == equipment.product_id and
                          p.description == equipment.description)
            if exist_line:
                exist_line.product_qty += equipment.quantity
                exist_line.equipment_amount_total += equipment.subtotal
            else:
                self.material_equipment_ids = [(0, 0, {
                    'project_scope': equipment.project_scope.id,
                    'section_name': equipment.section_name.id,
                    'variable_ref': equipment.variable_ref.id,
                    'group_of_product': equipment.group_of_product.id,
                    'product_id': equipment.product_id.id,
                    'description': equipment.description,
                    'product_qty': equipment.quantity,
                    'uom_id': equipment.uom_id.id,
                    'price_unit': equipment.unit_price,
                    'equipment_amount_total': equipment.subtotal,
                })]

    # amount material ---------------------
    @api.depends('material_ids')
    def _amount_material(self):
        for sheet in self:
            amount_material = 0.0
            amount_res_material = 0.0
            amount_pur_material = 0.0
            amount_tra_material = 0.0
            amount_left_material = 0.0
            amount_used_material = 0.0
            amount_unused_material = 0.0
            for line in sheet.material_ids:
                amount_material += line.material_amount_total
                amount_res_material += line.reserved_amt
                amount_pur_material += line.purchased_amt
                amount_tra_material += line.transferred_amt
                amount_left_material += line.budgeted_amt_left
                amount_used_material += line.actual_used_amt
                amount_unused_material += line.unused_amt
            sheet.update({
                'material_budget_res': amount_res_material,
                'material_budget_pur': amount_pur_material,
                'material_budget_tra': amount_tra_material,
                'material_budget_left': amount_left_material,
                'material_budget_used': amount_used_material,
                'material_budget_unused': amount_unused_material,
                'amount_material': amount_material,
            })

    # amount labour ---------------------    
    @api.depends('material_labour_ids')
    def _amount_labour(self):
        for sheet in self:
            amount_labour = 0.0
            amount_res_labour = 0.0
            amount_pur_labour = 0.0
            amount_tra_labour = 0.0
            amount_left_labour = 0.0
            amount_used_labour = 0.0
            amount_unused_labour = 0.0
            for line in sheet.material_labour_ids:
                amount_labour += line.labour_amount_total
                amount_res_labour += line.reserved_amt
                amount_pur_labour += line.purchased_amt
                amount_tra_labour += line.transferred_amt
                amount_left_labour += line.budgeted_amt_left
                amount_used_labour += line.actual_used_amt
                amount_unused_labour += line.unused_amt
            sheet.update({
                'labour_budget_res': amount_res_labour,
                'labour_budget_pur': amount_pur_labour,
                'labour_budget_tra': amount_tra_labour,
                'labour_budget_left': amount_left_labour,
                'labour_budget_used': amount_used_labour,
                'labour_budget_unused': amount_unused_labour,
                'amount_labour': amount_labour,
            })

    # amount overhead ---------------------    
    @api.depends('material_overhead_ids')
    def _amount_overhead(self):
        for sheet in self:
            amount_overhead = 0.0
            amount_res_overhead = 0.0
            amount_pur_overhead = 0.0
            amount_tra_overhead = 0.0
            amount_left_overhead = 0.0
            amount_used_overhead = 0.0
            amount_unused_overhead = 0.0
            for line in sheet.material_overhead_ids:
                amount_overhead += line.overhead_amount_total
                amount_res_overhead += line.reserved_amt
                amount_pur_overhead += line.purchased_amt
                amount_tra_overhead += line.transferred_amt
                amount_left_overhead += line.budgeted_amt_left
                amount_used_overhead += line.actual_used_amt
                amount_unused_overhead += line.unused_amt
            sheet.update({
                'overhead_budget_res': amount_res_overhead,
                'overhead_budget_pur': amount_pur_overhead,
                'overhead_budget_tra': amount_tra_overhead,
                'overhead_budget_left': amount_left_overhead,
                'overhead_budget_used': amount_used_overhead,
                'overhead_budget_unused': amount_unused_overhead,
                'amount_overhead': amount_overhead,
            })

    # amount subcon ---------------------    
    @api.depends('material_subcon_ids')
    def _amount_subcon(self):
        for sheet in self:
            amount_subcon = 0.0
            amount_res_subcon = 0.0
            amount_pur_subcon = 0.0
            amount_left_subcon = 0.0
            amount_used_subcon = 0.0
            amount_unused_subcon = 0.0
            for line in sheet.material_subcon_ids:
                amount_subcon += line.subcon_amount_total
                amount_res_subcon += line.reserved_amt
                amount_pur_subcon += line.purchased_amt
                amount_left_subcon += line.budgeted_amt_left
                amount_used_subcon += line.actual_used_amt
                amount_unused_subcon += line.unused_amt
            sheet.update({
                'subcon_budget_res': amount_res_subcon,
                'subcon_budget_pur': amount_pur_subcon,
                'subcon_budget_left': amount_left_subcon,
                'subcon_budget_used': amount_used_subcon,
                'subcon_budget_unused': amount_unused_subcon,
                'amount_subcon': amount_subcon,
            })

    # amount equipment ---------------------
    @api.depends('material_equipment_ids')
    def _amount_equipment(self):
        for sheet in self:
            amount_equipment = 0.0
            amount_res_equipment = 0.0
            amount_pur_equipment = 0.0
            amount_left_equipment = 0.0
            amount_used_equipment = 0.0
            amount_unused_equipment = 0.0
            for line in sheet.material_equipment_ids:
                amount_equipment += line.equipment_amount_total
                amount_res_equipment += line.reserved_amt
                amount_pur_equipment += line.purchased_amt
                amount_left_equipment += line.budgeted_amt_left
                amount_used_equipment += line.actual_used_amt
                amount_unused_equipment += line.unused_amt
            sheet.update({
                'equipment_budget_res': amount_res_equipment,
                'equipment_budget_pur': amount_pur_equipment,
                'equipment_budget_left': amount_left_equipment,
                'equipment_budget_used': amount_used_equipment,
                'equipment_budget_unused': amount_unused_equipment,
                'amount_equipment': amount_equipment,
            })

    # amount internal asset ---------------------    
    @api.depends('internal_asset_ids')
    def _amount_internal_asset(self):
        for sheet in self:
            amount_asset = 0.0
            amount_left_asset = 0.0
            amount_used_asset = 0.0
            amount_unused_asset = 0.0
            for line in sheet.internal_asset_ids:
                amount_asset += line.budgeted_amt
                amount_left_asset += line.budgeted_amt_left
                amount_used_asset += line.actual_used_amt
                amount_unused_asset += line.unused_amt
            sheet.update({
                'internas_budget_left': amount_left_asset,
                'internas_budget_used': amount_used_asset,
                'internas_budget_unused': amount_unused_asset,
                'amount_internal_asset': amount_asset,
            })

    # amount lumpsum ---------------------
    @api.depends('contract_history_ids.subtotal', 'material_budget_res', 'labour_budget_res', 'overhead_budget_res',
                 'subcon_budget_res',
                 'equipment_budget_res', 'material_budget_pur', 'labour_budget_pur', 'labour_budget_pur',
                 'subcon_budget_pur', 'equipment_budget_pur',
                 'material_budget_tra', 'labour_budget_tra', 'overhead_budget_tra', 'material_budget_left',
                 'labour_budget_left', 'overhead_budget_left',
                 'subcon_budget_left', 'equipment_budget_left', 'internas_budget_left', 'material_budget_unused',
                 'labour_budget_unused', 'overhead_budget_unused',
                 'subcon_budget_unused', 'equipment_budget_unused', 'internas_budget_unused', 'material_budget_used',
                 'labour_budget_used', 'overhead_budget_used',
                 'subcon_budget_used', 'equipment_budget_used', 'internas_budget_used')
    def _amount_contract(self):
        for sheet in self:
            reserved_budget = 0.00
            purchased_budget = 0.00
            transferred_budget = 0.00
            left_budget = 0.00
            unused_budget = 0.00
            used_budget = 0.00
            total = 0.00
            for line in sheet.contract_history_ids:
                if line.contract_category == 'main':
                    total += line.subtotal + line.contract_history.adjustment_sub - line.contract_history.discount_sub
                else:
                    total += line.total_variation_order + line.contract_history.adjustment_sub - line.contract_history.discount_sub
            reserved_budget = sheet.material_budget_res + sheet.labour_budget_res + sheet.overhead_budget_res + sheet.subcon_budget_res + sheet.equipment_budget_res
            purchased_budget = sheet.material_budget_pur + sheet.labour_budget_pur + sheet.overhead_budget_pur + sheet.subcon_budget_pur + sheet.equipment_budget_pur
            transferred_budget = sheet.material_budget_tra + sheet.labour_budget_tra + sheet.overhead_budget_tra
            left_budget = sheet.material_budget_left + sheet.labour_budget_left + sheet.overhead_budget_left + sheet.subcon_budget_left + sheet.equipment_budget_left + sheet.internas_budget_left
            unused_budget = sheet.material_budget_unused + sheet.labour_budget_unused + sheet.overhead_budget_unused + sheet.subcon_budget_unused + sheet.equipment_budget_unused + sheet.internas_budget_unused
            used_budget = sheet.material_budget_used + sheet.labour_budget_used + sheet.overhead_budget_used + sheet.subcon_budget_used + sheet.equipment_budget_used + sheet.internas_budget_used

            sheet.update({
                'contract_budget_res': reserved_budget,
                'contract_budget_pur': purchased_budget,
                'contract_budget_tra': transferred_budget,
                'contract_budget_left': left_budget,
                'contract_budget_unused': unused_budget,
                'contract_budget_used': used_budget,
                'amount_contract': total,
            })

    @api.depends('contract_history_ids.contract_history', 'amount_total')
    def _amount_revenue(self):
        for sheet in self:
            # if len(sheet.contract_history_ids) > 0:
            #     line = sheet.contract_history_ids[-1]
            #     exp_rev += (line.contract_history.amount_untaxed - line.contract_history.discount_sub + line.contract_history.adjustment_sub)
            #     total += (line.contract_history.amount_untaxed)
            exp_rev = sheet.amount_contract_total
            exp_profit = exp_rev - sheet.amount_total
            sheet.update({
                'contract_exp_revenue': exp_rev,
                'contract_exp_profit': exp_profit,
            })

    # amount internal transfer budget
    @api.depends('history_pbt_ids.allocation_amount', 'history_pbt_ids.send_amount')
    def _amount_free_project(self):
        for res in self:
            project_amt = 0.0
            receive_amt = 0.0
            send_amt = 0.0
            for line in res.history_pbt_ids:
                project_amt += line.allocation_amount
                # send_amt += line.send_amount
            # project_amt = receive_amt - send_amt
            res.amount_from_project = project_amt
            # res.update({'amount_from_project': round(project_amt)})

    @api.depends('history_pbt_ids.allocation_amount', 'history_pbt_ids.send_amount')
    def _amount_send_project(self):
        for res in self:
            project_amt = 0.0
            receive_amt = 0.0
            send_amt = 0.0
            for line in res.history_pbt_ids:
                # project_amt += line.allocation_amount
                send_amt += line.send_amount
            # project_amt = receive_amt - send_amt
            res.amount_send_project = send_amt
            # res.update({'amount_from_project': round(project_amt)})

    @api.depends('history_itb_ids.free_amt')
    def _amount_free_adjusted(self):
        for res in self:
            freea = 0.00
            freeb = 0.00
            for line in res.internal_transfer_budget_line_ids:
                freea += line.adjusted
            for line in res.project_budget_transfer_line_ids:
                freeb += line.adjusted
            res.amount_from_adjusted = (freea + freeb) * -1
            # res.update({'amount_free': round(free_amt)})

    @api.depends('amount_from_adjusted', 'amount_from_project', 'amount_total')
    def _amount_free(self):
        for res in self:
            free_amt = 0.00
            free_amt = res.amount_contract - res.amount_total
            if res.project_budget_transfer_line_ids or res.history_pbt_ids:
                free_amt += res.amount_from_project
                free_amt -= res.amount_send_project
            free_amt += res.amount_from_budget

            amount_from_adjusted = 0.00
            for item in res.internal_transfer_budget_line_ids:
                if (item.cur_unit_price == item.adj_unit_price or
                    (
                            item.is_newly_added_product and item.cur_unit_price == item.adj_unit_price and item.cur_qty == item.adj_qty)
                    and (not item.is_not_from_cost_sheet and item.cur_unit_price == item.adj_unit_price)) \
                        and item.cur_qty == item.adj_qty:
                    amount_from_adjusted += item.adjusted
            free_amt += amount_from_adjusted * -1
            res.amount_free = free_amt

    @api.depends('contract_history_ids', 'department_type')
    def _get_amount_total_contract(self):
        for res in self:
            if res.department_type == 'project':
                if res.contract_history_ids:
                    res.amount_contract_material = 0
                    res.amount_contract_labour = 0
                    res.amount_contract_overhead = 0
                    res.amount_contract_asset = 0
                    res.amount_contract_equipment = 0
                    res.amount_contract_subcon = 0
                    res.adjustment_sub = 0
                    res.discount_sub = 0
                    res.amount_contract_total = 0
                    for contract in res.contract_history_ids.contract_history:
                        if contract.contract_category == 'main':
                            res.amount_contract_material += contract.total_material
                            res.amount_contract_labour += contract.total_labour
                            res.amount_contract_overhead += contract.total_overhead
                            res.amount_contract_asset += contract.total_internal_asset
                            res.amount_contract_equipment += contract.total_equipment
                            res.amount_contract_subcon += contract.total_subcon

                            res.adjustment_sub += contract.adjustment_sub
                            res.discount_sub += contract.discount_sub

                            res.amount_contract_total += contract.amount_untaxed + res.adjustment_sub - res.discount_sub

                        elif contract.contract_category == 'var':
                            res.amount_contract_material += contract.total_variation_order_material
                            res.amount_contract_labour += contract.total_variation_order_labour
                            res.amount_contract_overhead += contract.total_variation_order_overhead
                            res.amount_contract_asset += contract.total_variation_order_asset
                            res.amount_contract_equipment += contract.total_variation_order_equipment
                            res.amount_contract_subcon += contract.total_variation_order_subcon

                            res.adjustment_sub += contract.adjustment_sub
                            res.discount_sub += contract.discount_sub

                            res.amount_contract_total += contract.total_variation_order + res.adjustment_sub - res.discount_sub

    @api.depends('contract_history_ids', 'department_type', 'project_scope_cost_ids', 'section_cost_ids')
    def _get_amount_total_contract_scope_section(self):
        for rec in self:
            if rec.department_type == 'project':
                scope_contract_total = 0
                section_contract_total = 0
                if rec.contract_history_ids:
                    if rec.project_scope_cost_ids:
                        scope_contract_total = sum(rec.project_scope_cost_ids.mapped('subtotal'))
                        # Amount contract each scope line
                        for scope in rec.project_scope_cost_ids:
                            scope_amount_contract = 0
                            for contract in rec.contract_history_ids:
                                if contract.contract_category == 'main':
                                    for contract_scope in contract.contract_history.project_scope_ids:
                                        if scope.project_scope_id.id == contract_scope.project_scope.id:
                                            scope_amount_contract += contract_scope.subtotal_scope
                                elif contract.contract_category == 'var':
                                    for material in contract.contract_history.material_line_ids:
                                        if scope.project_scope_id.id == material.project_scope.id:
                                            scope_amount_contract += (material.quantity * material.unit_price)
                                    for labour in contract.contract_history.labour_line_ids:
                                        if scope.project_scope_id.id == labour.project_scope.id:
                                            scope_amount_contract += (labour.quantity * labour.unit_price)
                                    for overhead in contract.contract_history.overhead_line_ids:
                                        if scope.project_scope_id.id == overhead.project_scope.id:
                                            scope_amount_contract += (overhead.quantity * overhead.unit_price)
                                    for asset in contract.contract_history.internal_asset_line_ids:
                                        if scope.project_scope_id.id == asset.project_scope.id:
                                            scope_amount_contract += (asset.quantity * asset.unit_price)
                                    for equipment in contract.contract_history.equipment_line_ids:
                                        if scope.project_scope_id.id == equipment.project_scope.id:
                                            scope_amount_contract += (equipment.quantity * equipment.unit_price)
                                    for subcon in contract.contract_history.subcon_line_ids:
                                        if scope.project_scope_id.id == subcon.project_scope.id:
                                            scope_amount_contract += (subcon.quantity * subcon.unit_price)

                            self.env.cr.execute(
                                "UPDATE project_scope_cost SET amount_contract = %s WHERE id = %s",
                                (scope_amount_contract, scope.id))

                        if rec.section_cost_ids:
                            section_contract_total = sum(rec.section_cost_ids.mapped('subtotal'))

                            # Amount contract each section line
                            for section in rec.section_cost_ids:
                                section_amount_contract = 0
                                for contract in rec.contract_history_ids:
                                    if contract.contract_category == 'main':
                                        for contract_section in contract.contract_history.section_ids:
                                            if (section.project_scope_id.id == contract_section.project_scope.id
                                                    and section.section_id.id == contract_section.section.id):
                                                section_amount_contract += contract_section.subtotal_section
                                    elif contract.contract_category == 'var':
                                        for material in contract.contract_history.material_line_ids:
                                            if (section.project_scope_id.id == material.project_scope.id
                                                    and section.section_id.id == material.section_name.id):
                                                section_amount_contract += (material.quantity * material.unit_price)
                                        for labour in contract.contract_history.labour_line_ids:
                                            if (section.project_scope_id.id == labour.project_scope.id
                                                    and section.section_id == labour.section_name.id):
                                                section_amount_contract += (labour.quantity * labour.unit_price)
                                        for overhead in contract.contract_history.overhead_line_ids:
                                            if (section.project_scope_id.id == overhead.project_scope.id
                                                    and section.section_id == overhead.section_name.id):
                                                section_amount_contract += (overhead.quantity * overhead.unit_price)
                                        for asset in contract.contract_history.internal_asset_line_ids:
                                            if (section.project_scope_id.id == asset.project_scope.id
                                                    and section.section_id == asset.section_name.id):
                                                section_amount_contract += (asset.quantity * asset.unit_price)
                                        for equipment in contract.contract_history.equipment_line_ids:
                                            if (section.project_scope_id.id == equipment.project_scope.id
                                                    and section.section_id == equipment.section_name.id):
                                                section_amount_contract += (equipment.quantity * equipment.unit_price)
                                        for subcon in contract.contract_history.subcon_line_ids:
                                            if (section.project_scope_id.id == subcon.project_scope.id
                                                    and section.section_id == subcon.section_name.id):
                                                section_amount_contract += (subcon.quantity * subcon.unit_price)

                                # section.write({
                                #     'amount_contract': section_amount_contract,
                                # })
                                # convert above code to query
                                self.env.cr.execute(
                                    "UPDATE section_cost SET amount_contract = %s WHERE id = %s",
                                    (section_amount_contract, section.id))

                rec.amount_contract_scope = scope_contract_total
                rec.amount_contract_section = section_contract_total
            elif rec.department_type == 'department':
                scope_contract_total = 0
                section_contract_total = 0
                if rec.contract_history_ids:
                    if rec.project_scope_cost_ids:
                        scope_contract_total = sum(rec.project_scope_cost_ids.mapped('subtotal'))

                        # Amount contract each scope line
                        for scope in rec.project_scope_cost_ids:
                            scope_amount_contract = 0
                            for contract in rec.contract_history_ids.job_estimate:
                                if contract.contract_category == 'main':
                                    for contract_scope in contract.project_scope_ids:
                                        if scope.project_scope_id.id == contract_scope.project_scope.id:
                                            scope_amount_contract += contract_scope.subtotal
                                elif contract.contract_category == 'var':
                                    for material in contract.material_estimation_ids:
                                        if scope.project_scope_id.id == material.project_scope.id:
                                            scope_amount_contract += material.subtotal
                                    for labour in contract.labour_estimation_ids:
                                        if scope.project_scope_id.id == labour.project_scope.id:
                                            scope_amount_contract += labour.subtotal
                                    for overhead in contract.overhead_estimation_ids:
                                        if scope.project_scope_id.id == overhead.project_scope.id:
                                            scope_amount_contract += overhead.subtotal
                                    for asset in contract.internal_asset_ids:
                                        if scope.project_scope_id.id == asset.project_scope.id:
                                            scope_amount_contract += asset.subtotal
                                    for equipment in contract.equipment_estimation_ids:
                                        if scope.project_scope_id.id == equipment.project_scope.id:
                                            scope_amount_contract += equipment.subtotal
                                    for subcon in contract.subcon_estimation_ids:
                                        if scope.project_scope_id.id == subcon.project_scope.id:
                                            scope_amount_contract += subcon.subtotal
                            # scope.write({
                            #     'amount_contract': scope_amount_contract,
                            # })
                            # convert above code to query
                            self.env.cr.execute(
                                "UPDATE project_scope_cost SET amount_contract = %s WHERE id = %s",
                                (scope_amount_contract, scope.id))

                        if rec.section_cost_ids:
                            section_contract_total = sum(rec.section_cost_ids.mapped('subtotal'))

                            # Amount contract each section line
                            for section in rec.section_cost_ids:
                                section_amount_contract = 0
                                for contract in rec.contract_history_ids.job_estimate:
                                    if contract.contract_category == 'main':
                                        for contract_section in contract.section_ids:
                                            if (section.project_scope_id.id == contract_section.project_scope.id
                                                    and section.section_id.id == contract_section.section_name.id):
                                                section_amount_contract += contract_section.subtotal
                                    elif contract.contract_category == 'var':
                                        for material in contract.material_estimation_ids:
                                            if (section.project_scope_id.id == material.project_scope.id
                                                    and section.section_id.id == material.section_name.id):
                                                section_amount_contract += material.subtotal
                                        for labour in contract.labour_estimation_ids:
                                            if (section.project_scope_id.id == labour.project_scope.id
                                                    and section.section_id.id == labour.section_name.id):
                                                section_amount_contract += labour.subtotal
                                        for overhead in contract.overhead_estimation_ids:
                                            if (section.project_scope_id.id == overhead.project_scope.id
                                                    and section.section_id.id == overhead.section_name.id):
                                                section_amount_contract += overhead.subtotal
                                        for asset in contract.internal_asset_ids:
                                            if (section.project_scope_id.id == asset.project_scope.id
                                                    and section.section_id.id == asset.section_name.id):
                                                section_amount_contract += asset.subtotal
                                        for equipment in contract.equipment_estimation_ids:
                                            if (section.project_scope_id.id == equipment.project_scope.id
                                                    and section.section_id.id == equipment.section_name.id):
                                                section_amount_contract += equipment.subtotal
                                        for subcon in contract.subcon_estimation_ids:
                                            if (section.project_scope_id.id == subcon.project_scope.id
                                                    and section.section_id.id == subcon.section_name.id):
                                                section_amount_contract += subcon.subtotal
                                # section.write({
                                #     'amount_contract': section_amount_contract,
                                # })
                                # convert above code to query
                                self.env.cr.execute(
                                    "UPDATE section_cost SET amount_contract = %s WHERE id = %s",
                                    (section_amount_contract, section.id))

                rec.amount_contract_scope = scope_contract_total
                rec.amount_contract_section = section_contract_total

    @api.depends('amount_material', 'amount_labour',
                 'amount_subcon', 'amount_overhead',
                 'amount_equipment', 'amount_internal_asset')
    def _amount_total(self):
        for cost_sheet in self:
            cost_sheet.amount_total = (
                    cost_sheet.amount_material + cost_sheet.amount_labour + cost_sheet.amount_subcon +
                    cost_sheet.amount_overhead + cost_sheet.amount_equipment + cost_sheet.amount_internal_asset)

    def _comute_job_estimate(self):
        for rec in self:
            # job_count = self.env['job.estimate'].search_count(
            #     [('project_id', '=', self.project_id.id), ('sale_state', '=', 'sale')])
            # convert above code to query
            rec.env.cr.execute(
                "SELECT count(*) FROM job_estimate WHERE project_id = %s AND sale_state = 'sale'",
                (rec.project_id.id,))
            job_count = rec.env.cr.fetchone()[0]
            rec.total_job_estimate = job_count

    def _comute_sales_orders(self):
        for order in self:
            # order_count = self.env['sale.order.const'].search_count(
            #     [('project_id', '=', self.project_id.id), ('state', '=', ('sale', 'done'))])
            # convert above code to query
            order.env.cr.execute(
                "SELECT count(*) FROM sale_order_const WHERE project_id = %s AND state IN ('sale', 'done')",
                (order.project_id.id,))
            order_count = order.env.cr.fetchone()[0]
            order.total_sale_order = order_count

    def _comute_project_budget(self):
        for rec in self:
            # project_budget_count = self.env['project.budget'].search_count([('cost_sheet', '=', rec.id)])
            # convert above code to query
            self.env.cr.execute(
                "SELECT count(*) FROM project_budget WHERE cost_sheet = %s",
                (rec.id,))
            project_budget_count = self.env.cr.fetchone()[0]
            rec.total_project_budget = project_budget_count

    def _comute_budget_change_request(self):
        for rec in self:
            # budget_change_request_count = self.env['internal.transfer.budget'].search_count(
            #     [('job_sheet_id', '=', rec.id), ('is_project_transfer', '=', False)])
            # convert above code to query
            self.env.cr.execute(
                "SELECT count(*) FROM internal_transfer_budget WHERE job_sheet_id = %s AND is_project_transfer = FALSE",
                (rec.id,))
            budget_change_request_count = self.env.cr.fetchone()[0]
            rec.total_budget_change_request = budget_change_request_count

    def _comute_project_budget_transfer(self):
        for rec in self:
            # project_budget_transfer = self.env['internal.transfer.budget'].search_count(
            #     [('job_sheet_id', '=', rec.id), ('is_project_transfer', '=', True)])
            # convert above code to query
            self.env.cr.execute(
                "SELECT count(*) FROM internal_transfer_budget WHERE job_sheet_id = %s AND is_project_transfer = TRUE",
                (rec.id,))
            project_budget_transfer = self.env.cr.fetchone()[0]
            rec.total_project_budget_transfer = project_budget_transfer

    def create_project_budget(self):
        for record in self:
            context = {
                'default_project_id': record.project_id.id,
                'default_analytic_group_id': record.account_tag_ids.ids,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Periodical Budget',
                'view_mode': 'form',
                'res_model': 'project.budget',
                'context': context,
            }

    def create_internal_transfer_budget(self):
        for record in self:
            context = {
                'default_is_project_transfer': False,
                'default_is_change_allocation': False,
                'default_project_id': record.project_id.id,
                'default_branch_id': record.branch_id.id,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Budget Change Request',
                'view_mode': 'form',
                'res_model': 'internal.transfer.budget',
                'context': context,
                'target': 'current',
            }

    def create_project_budget_transfer(self):
        for record in self:
            context = {
                'default_is_project_transfer': True,
                'default_is_change_allocation': False,
                'default_project_id': record.project_id.id,
                'default_branch_id': record.branch_id.id,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Project Budget Transfer',
                'view_mode': 'form',
                'res_model': 'internal.transfer.budget',
                'context': context,
                'target': 'current',
            }

    def create_change_allocation_request(self):
        for rec in self:
            context = {
                'default_is_project_transfer': False,
                'default_is_change_allocation': True,
                'default_project_id': rec.project_id.id,
                'default_branch_id': rec.branch_id.id,

            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Change Allocation Budget',
                'view_mode': 'form',
                'res_model': 'internal.transfer.budget',
                'context': context,
                'target': 'current',
            }

    def action_job_estimate(self):
        return {
            'name': ("BOQ"),
            'view_mode': 'tree,form',
            'res_model': 'job.estimate',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_id', '=', self.project_id.id), ('state', '=', 'sale')],
        }

    def action_sale_order(self):
        return {
            'name': ("Contracts"),
            'view_mode': 'tree,form',
            'res_model': 'sale.order.const',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_id', '=', self.project_id.id), ('state', '=', ('sale', 'done'))],
        }

    def action_project_budget(self):
        return {
            'name': ("Periodical Budget"),
            'view_mode': 'tree,form',
            'res_model': 'project.budget',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('cost_sheet', '=', self.id)],
        }

    def action_budget_change_request(self):
        return {
            'name': "Budget Change Request",
            'view_mode': 'tree,form',
            'res_model': 'internal.transfer.budget',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('job_sheet_id', '=', self.id), ('is_project_transfer', '=', False)],
        }

    def action_project_budget_transfer(self):
        return {
            'name': "Project Budget Transfer",
            'view_mode': 'tree,form',
            'res_model': 'internal.transfer.budget',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('job_sheet_id', '=', self.id), ('is_project_transfer', '=', True)],
        }

    def button_reset_estimation(self):
        for rec in self:
            rec.material_ids.unlink()
            rec.material_labour_ids.unlink()
            rec.material_overhead_ids.unlink()
            rec.material_subcon_ids.unlink()
            rec.material_equipment_ids.unlink()
            rec.internal_asset_ids.unlink()
            rec.project_scope_cost_ids.unlink()
            rec.section_cost_ids.unlink()

            rec.set_scope_section_table()

    # def button_material_claim_budget(self):
    #     for rec in self:
    #         if rec.budgeting_period == 'project':
    #             free_amt = 0.00
    #             for line in rec.material_ids.filtered(lambda p: p.is_has_budget_left is True):
    #                 free_amt += line.budgeted_amt_left
    #                 line.write({'amount_return': line.budgeted_amt_left,
    #                             'is_has_budget_left': False,})
    #                 if rec.budgeting_method == 'gop_budget':
    #                     cost_sheet_material_gop = rec.material_gop_ids.filtered(
    #                         lambda p: p.group_of_product.id == line.group_of_product.id)
    #                     cost_sheet_material_gop.amount_return += line.budgeted_amt_left
    #                     cost_sheet_material_gop._budget_amount_left()
    #                 rec.write({
    #                     'material_budget_claim_history_cost_ids': [(0, 0, {
    #                         'job_sheet_id': rec.id,
    #                         'type': 'material',
    #                         'project_scope_id': line.project_scope.id,
    #                         'section_id': line.section_name.id,
    #                         'group_of_product_id': line.group_of_product.id,
    #                         'product_id': line.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': line.uom_id.id,
    #                         'budget_amount': line.material_amount_total,
    #                         'budget_claim_amount': line.amount_return,
    #                     })],
    #                 })
    #                 line._budget_amount_left()
    #             if free_amt > 0:
    #                 rec.write({
    #                     'amount_from_budget': rec.amount_from_budget + free_amt,
    #                 })
    #         else:
    #             periodical_budgets = rec.periodical_budget_ids.filtered(lambda p: p.is_material_has_budget_left is True)
    #             for budget in periodical_budgets:
    #                 budget.button_material_claim_budget()
    #
    # def button_labour_claim_budget(self):
    #     for rec in self:
    #         if rec.budgeting_period == 'project':
    #             free_amt = 0.00
    #             for line in rec.material_labour_ids.filtered(lambda p: p.is_has_budget_left is True):
    #                 free_amt += line.budgeted_amt_left
    #                 line.write({'amount_return': line.budgeted_amt_left,
    #                             'is_has_budget_left': False,})
    #                 if rec.budgeting_method == 'gop_budget':
    #                     cost_sheet_labour_gop = rec.material_labour_gop_ids.filtered(
    #                         lambda p: p.group_of_product.id == line.group_of_product.id)
    #                     cost_sheet_labour_gop.amount_return += line.budgeted_amt_left
    #                     cost_sheet_labour_gop._budget_amount_left()
    #                 rec.write({
    #                     'labour_budget_claim_history_cost_ids': [(0, 0, {
    #                         'job_sheet_id': rec.id,
    #                         'type': 'labour',
    #                         'project_scope_id': line.project_scope.id,
    #                         'section_id': line.section_name.id,
    #                         'group_of_product_id': line.group_of_product.id,
    #                         'product_id': line.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': line.uom_id.id,
    #                         'budget_amount': line.labour_amount_total,
    #                         'budget_claim_amount': line.amount_return,
    #                     })],
    #                 })
    #                 line._budget_amount_left()
    #             if free_amt > 0:
    #                 rec.write({
    #                     'amount_from_budget': rec.amount_from_budget + free_amt,
    #                 })
    #         else:
    #             periodical_budgets = rec.periodical_budget_ids.filtered(lambda p: p.is_labour_has_budget_left is True)
    #             for budget in periodical_budgets:
    #                 budget.button_labour_claim_budget()
    #
    # def button_overhead_claim_budget(self):
    #     for rec in self:
    #         if rec.budgeting_period == 'project':
    #             free_amt = 0.00
    #             for line in rec.material_overhead_ids.filtered(lambda p: p.is_has_budget_left is True):
    #                 free_amt += line.budgeted_amt_left
    #                 line.write({'amount_return': line.budgeted_amt_left,
    #                             'is_has_budget_left': False,})
    #                 if rec.budgeting_method == 'gop_budget':
    #                     cost_sheet_overhead_gop = rec.material_overhead_gop_ids.filtered(
    #                         lambda p: p.group_of_product.id == line.group_of_product.id)
    #                     cost_sheet_overhead_gop.amount_return += line.budgeted_amt_left
    #                     cost_sheet_overhead_gop._budget_amount_left()
    #                 rec.write({
    #                     'overhead_budget_claim_history_cost_ids': [(0, 0, {
    #                         'job_sheet_id': rec.id,
    #                         'type': 'overhead',
    #                         'project_scope_id': line.project_scope.id,
    #                         'section_id': line.section_name.id,
    #                         'group_of_product_id': line.group_of_product.id,
    #                         'product_id': line.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': line.uom_id.id,
    #                         'budget_amount': line.overhead_amount_total,
    #                         'budget_claim_amount': line.amount_return,
    #                     })],
    #                 })
    #                 line._budget_amount_left()
    #             if free_amt > 0:
    #                 rec.write({
    #                     'amount_from_budget': rec.amount_from_budget + free_amt,
    #                 })
    #         else:
    #             periodical_budgets = rec.periodical_budget_ids.filtered(lambda p: p.is_overhead_has_budget_left is True)
    #             for budget in periodical_budgets:
    #                 budget.button_overhead_claim_budget()
    #
    # def button_equipment_claim_budget(self):
    #     for rec in self:
    #         if rec.budgeting_period == 'project':
    #             free_amt = 0.00
    #             for line in rec.material_equipment_ids.filtered(lambda p: p.is_has_budget_left is True):
    #                 free_amt += line.budgeted_amt_left
    #                 line.write({'amount_return': line.budgeted_amt_left,
    #                             'is_has_budget_left': False,})
    #                 if rec.budgeting_method == 'gop_budget':
    #                     cost_sheet_equipment_gop = rec.material_equipment_gop_ids.filtered(
    #                         lambda p: p.group_of_product.id == line.group_of_product.id)
    #                     cost_sheet_equipment_gop.amount_return += line.budgeted_amt_left
    #                     cost_sheet_equipment_gop._budget_amount_left()
    #                 rec.write({
    #                     'equipment_budget_claim_history_cost_ids': [(0, 0, {
    #                         'job_sheet_id': rec.id,
    #                         'type': 'equipment',
    #                         'project_scope_id': line.project_scope.id,
    #                         'section_id': line.section_name.id,
    #                         'group_of_product_id': line.group_of_product.id,
    #                         'product_id': line.product_id.id,
    #                         'subcon_id': False,
    #                         'uom_id': line.uom_id.id,
    #                         'budget_amount': line.equipment_amount_total,
    #                         'budget_claim_amount': line.amount_return,
    #                     })],
    #                 })
    #                 line._budget_amount_left()
    #             if free_amt > 0:
    #                 rec.write({
    #                     'amount_from_budget': rec.amount_from_budget + free_amt,
    #                 })
    #         else:
    #             periodical_budgets = rec.periodical_budget_ids.filtered(lambda p: p.is_equipment_has_budget_left is True)
    #             for budget in periodical_budgets:
    #                 budget.button_equipment_claim_budget()
    #
    # def button_subcon_claim_budget(self):
    #     for rec in self:
    #         if rec.budgeting_period == 'project':
    #             free_amt = 0.00
    #             for line in rec.material_subcon_ids.filtered(lambda p: p.is_has_budget_left is True):
    #                 free_amt += line.budgeted_amt_left
    #                 line.write({'amount_return': line.budgeted_amt_left,
    #                             'is_has_budget_left': False,})
    #                 rec.write({
    #                     'subcon_budget_claim_history_cost_ids': [(0, 0, {
    #                         'job_sheet_id': rec.id,
    #                         'type': 'subcon',
    #                         'project_scope_id': line.project_scope.id,
    #                         'section_id': line.section_name.id,
    #                         'subcon_id': line.variable.id,
    #                         'uom_id': line.uom_id.id,
    #                         'budget_amount': line.subcon_amount_total,
    #                         'budget_claim_amount': line.amount_return,
    #                     })],
    #                 })
    #                 line._budget_amount_left()
    #             if free_amt > 0:
    #                 rec.write({
    #                     'amount_from_budget': rec.amount_from_budget + free_amt,
    #                 })
    #         else:
    #             periodical_budgets = rec.periodical_budget_ids.filtered(lambda p: p.is_subcon_has_budget_left is True)
    #             for budget in periodical_budgets:
    #                 budget.button_subcon_claim_budget()

    #  action freeze & unfreeze ----------
    def ba_freeze_job_cost(self):
        self.ba_freeze_state = True
        if self.project_id:
            filtered_proj_budget = self.env['project.budget'].search([('cost_sheet', '=', self.id)])
            if filtered_proj_budget:
                for rec in filtered_proj_budget:
                    rec.ba_freeze_project_budget = True
                    rec.state = 'freeze'
        return self.write({'state': 'freeze'})

    def ba_unfreeze_job_cost(self):
        self.ba_freeze_state = False
        if self.project_id:
            filtered_proj_budget = self.env['project.budget'].search([('cost_sheet', '=', self.id)])
            if filtered_proj_budget:
                for rec in filtered_proj_budget:
                    rec.ba_freeze_project_budget = False
                    rec.state = 'in_progress'
        return self.write({'state': 'in_progress'})

    def cost_sheet_print(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/equip3_construction_operation/cost_sheet_report/%s' % self.id,
            'target': 'self',
        }

    # Validation cannot add line same as existing line
    @api.onchange('material_ids')
    def _check_exist_group_of_product_material(self):
        exist_section_group_list_material = []
        for line in self.material_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_material):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_material.append(same)

    @api.onchange('material_labour_ids')
    def _check_exist_group_of_product_labour(self):
        exist_section_group_list_labour1 = []
        for line in self.material_labour_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_labour1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_labour1.append(same)

    @api.onchange('material_overhead_ids')
    def _check_exist_group_of_product_overhead(self):
        exist_section_group_list_overhead = []
        for line in self.material_overhead_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_overhead):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_overhead.append(same)

    @api.onchange('material_equipment_ids')
    def _check_exist_group_of_product_equipment(self):
        exist_section_group_list_equipment1 = []
        for line in self.material_equipment_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_equipment1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_equipment1.append(same)

    @api.onchange('internal_asset_ids')
    def _check_exist_group_of_product_asset(self):
        exist_section_group_list_asset1 = []
        for line in self.internal_asset_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.asset_id.id)
            if (same in exist_section_group_list_asset1):
                raise ValidationError(
                    _('The Asset "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Asset selected.' % (
                        (line.asset_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_asset1.append(same)

    @api.onchange('material_subcon_ids')
    def _check_exist_subcon(self):
        exist_section_subcon_list_subcon = []
        for line in self.material_subcon_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.variable.id)
            if (same in exist_section_subcon_list_subcon):
                raise ValidationError(
                    _('The Job Subcon "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Job Subcon selected.' % (
                        (line.variable.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_subcon_list_subcon.append(same)

    @api.constrains('material_ids')
    def _check_exist_group_of_product_material_2(self):
        exist_section_group_list_material = []
        for line in self.material_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_material):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_material.append(same)

    @api.constrains('material_labour_ids')
    def _check_exist_group_of_product_labour_2(self):
        exist_section_group_list_labour1 = []
        for line in self.material_labour_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_labour1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_labour1.append(same)

    @api.constrains('material_overhead_ids')
    def _check_exist_group_of_product_overhead_2(self):
        exist_section_group_list_overhead = []
        for line in self.material_overhead_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_overhead):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_overhead.append(same)

    @api.constrains('material_equipment_ids')
    def _check_exist_group_of_product_equipment_2(self):
        exist_section_group_list_equipment1 = []
        for line in self.material_equipment_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_equipment1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_equipment1.append(same)

    @api.constrains('internal_asset_ids')
    def _check_exist_group_of_product_asset_2(self):
        exist_section_group_list_asset1 = []
        for line in self.internal_asset_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.asset_id.id)
            if (same in exist_section_group_list_asset1):
                raise ValidationError(
                    _('The Asset "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Asset selected.' % (
                        (line.asset_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_asset1.append(same)

    @api.constrains('material_subcon_ids')
    def _check_exist_subcon_2(self):
        exist_section_subcon_list_subcon = []
        for line in self.material_subcon_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.variable.id)
            if (same in exist_section_subcon_list_subcon):
                raise ValidationError(
                    _('The Job Subcon "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Job Subcon selected.' % (
                        (line.variable.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_subcon_list_subcon.append(same)

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


class CostSheetApproverUser(models.Model):
    _name = 'cost.sheet.approver.user'
    _description = "Cost Sheet Approver User"

    cost_sheet_approver_id = fields.Many2one('job.cost.sheet', string="Cost Sheet")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'cost_sheet_app_emp_ids', string="Approved user")
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
    matrix_user_ids = fields.Many2many('res.users', 'cost_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    # parent status
    state = fields.Selection(related='cost_sheet_approver_id.state', string='Parent Status')

    @api.depends('cost_sheet_approver_id')
    def fetch_sl_no(self):
        for line in self:
            no = 0
            line.name = no
            for l in line:
                no += 1
                l.name = no
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len(rec.user_ids) < rec.minimum_approver and rec.cost_sheet_approver_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.cost_sheet_approver_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids


class MaterialGopMaterial(models.Model):
    _name = 'material.gop.material'
    _description = "Material Gop"
    _order = 'sequence, id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    material_gop_amount_total = fields.Float(string='Budgeted Amount')
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    reserved_amt = fields.Float('Reserved Budget Amount')
    transferred_amt = fields.Float('Transferred Amount')
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Amount', default=0.00)
    product_amt_na = fields.Float('Unallocated Amount', default=0.00, compute="_product_amt_na")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    material_line_ids = fields.One2many('material.material', 'material_gop_id', string='Material')
    amount_return = fields.Float('Amount Return', default=0.00)

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

    @api.depends('job_sheet_id.material_gop_ids', 'job_sheet_id.material_gop_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.material_gop_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('material_gop_amount_total', 'actual_used_amt')
    def _unused_amt(self):
        total = 0
        for line in self:
            total = line.material_gop_amount_total - line.actual_used_amt
            line.unused_amt = total

    @api.depends('material_gop_amount_total', 'allocated_budget_amt')
    def _product_amt_na(self):
        total = 0
        for line in self:
            total = line.material_gop_amount_total - line.allocated_budget_amt
            line.product_amt_na = total

    @api.depends('material_gop_amount_total', 'reserved_amt', 'purchased_amt')
    def _budget_amount_left(self):
        total = 0
        for line in self:
            total = (line.material_gop_amount_total - line.reserved_amt - line.purchased_amt - line.amount_return - line.transferred_amt)
            line.budgeted_amt_left = total


class MaterialMaterial(models.Model):
    _inherit = 'material.material'
    _description = "Material"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    purchased_qty = fields.Float('Purchased Quantity', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    billed_qty = fields.Float('Billed Quantity', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    budgeted_qty_left = fields.Float('Budgeted Quantity Left', compute="_budget_quntity_left")
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    reserved_qty = fields.Float('Reserved Budget Quantity')
    reserved_amt = fields.Float('Reserved Budget Amount')
    transferred_qty = fields.Float('Transferred Quantity')
    transferred_amt = fields.Float('Transferred Amount')
    received_qty = fields.Float('Received Quantity')
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    actual_used_qty = fields.Float('Actual Used Quantity', default=0.00)
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    allocated_budget_qty = fields.Float('Allocated Quantity', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Amount', default=0.00)
    product_qty_na = fields.Float('Unallocated Quantity', default=0.00, compute="_product_qty_na")
    product_amt_na = fields.Float('Unallocated Amount', default=0.00, compute="_product_amt_na")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    on_hand_qty = fields.Float('On Hand Quantity', default=0.00, compute="_comute_on_hand")

    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    material_gop_id = fields.Many2one('material.gop.material', string="Material GOP ID", compute="_get_material_gop_id")
    project_scope_id = fields.Many2one('project.scope.cost', string="Project Scope",
                                       compute="_get_project_scope_id", store=True)
    section_id = fields.Many2one('section.cost', string="Section",
                                 compute="_get_section_id", store=True)

    on_hand_qty_converted = fields.Float('On Hand Quantity', default=0.00,
                                         compute="_compute_on_hand_converted")
    amount_return = fields.Float('Return Amount', default=0.00)
    reserved_return_amount = fields.Float('Reserved Return Amount', default=0.00)
    over_amount = fields.Float('Over Amount', default=0.00)
    reserved_over_amount = fields.Float('Reserved Over Amount', default=0.00)
    po_reserved_qty = fields.Float('PO Reserved Quantity', default=0.00)

    @api.depends('product_qty', 'price_unit')
    def compute_material_amount_total(self):
        for line in self:
            if line.purchased_qty > 0 or (line.reserved_qty > 0 and line.reserved_amt) or (line.transferred_qty and line.transferred_amt):
                current_quantity = line.product_qty - line.reserved_qty - line.purchased_qty - line.transferred_qty
                current_amount_total = current_quantity * line.price_unit
                if line.reserved_qty > 0 >= line.po_reserved_qty:
                    previous_unit_price = ((line.reserved_amt + line.purchased_amt + line.amount_return
                                            + line.transferred_amt + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.reserved_qty + line.purchased_qty + line.transferred_qty))
                else:
                    previous_unit_price = ((line.reserved_amt + line.purchased_amt + line.amount_return
                                           + line.transferred_amt + line.reserved_return_amount
                                           - line.reserved_over_amount - line.over_amount ) /
                                           (line.po_reserved_qty + line.purchased_qty + line.transferred_qty))
                previous_amount_total = previous_unit_price * (line.purchased_qty + line.reserved_qty + line.transferred_qty)
                line.material_amount_total = current_amount_total + previous_amount_total

            else:
                line.material_amount_total = line.product_qty * line.price_unit

    @api.depends('on_hand_qty', 'product_id', 'job_sheet_id.warehouse_id')
    def _compute_on_hand_converted(self):
        for rec in self:
            result_on_hand_qty = rec.on_hand_qty
            if rec.uom_id.category_id.name == 'Working Time':
                if rec.uom_id != rec.product_id.uom_id:
                    if rec.uom_id.name == 'Days':
                        result_on_hand_qty = rec.on_hand_qty / rec.project_id.working_hour_hours
                    elif rec.uom_id.name == 'Hours':
                        result_on_hand_qty = rec.on_hand_qty * rec.project_id.working_hour_hours
            rec.on_hand_qty_converted = result_on_hand_qty

    @api.depends('project_scope', 'section_name')
    def _get_section_id(self):
        for res in self:
            if res.project_scope:
                # section_line = self.env['section.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id),
                #      ('section_id', '=', res.section_name.id)], limit=1)
                # convert above code to filtered
                section_line = res.job_sheet_id.section_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id and p.section_id.id == res.section_name.id)
                if section_line:
                    res.section_id = section_line.id
                else:
                    res.section_id = False
            else:
                res.section_id = False

    @api.depends('project_scope')
    def _get_project_scope_id(self):
        for res in self:
            if res.project_scope:
                # scope_line = self.env['project.scope.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id)],
                #     limit=1)
                # convert above code to filtered
                scope_line = res.job_sheet_id.project_scope_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id)
                if scope_line:
                    res.project_scope_id = scope_line.id
                else:
                    res.project_scope_id = False
            else:
                res.project_scope_id = False

    @api.depends('project_scope', 'section_name', 'group_of_product')
    def _get_material_gop_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product:
                # gop_line = self.env['material.gop.material'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id)],
                #     limit=1)
                gop_line = res.job_sheet_id.material_gop_ids.filtered(
                    lambda p: p.project_scope.id == res.project_scope.id
                              and p.section_name.id == res.section_name.id
                              and p.group_of_product.id == res.group_of_product.id)
                if gop_line:
                    res.material_gop_id = gop_line[0].id
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

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'product')]}
            }

    @api.depends('job_sheet_id.material_ids', 'job_sheet_id.material_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.material_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('product_qty', 'actual_used_qty')
    def _unused_qty(self):
        total = 0
        for line in self:
            total = line.product_qty - line.actual_used_qty
            line.unused_qty = total

    @api.depends('material_amount_total', 'actual_used_amt')
    def _unused_amt(self):
        total = 0
        for line in self:
            total = line.material_amount_total - line.actual_used_amt
            line.unused_amt = total

    @api.depends('product_qty', 'allocated_budget_qty')
    def _product_qty_na(self):
        total = 0
        for line in self:
            total = line.product_qty - line.allocated_budget_qty
            line.product_qty_na = total

    @api.depends('material_amount_total', 'allocated_budget_amt')
    def _product_amt_na(self):
        total = 0
        for line in self:
            total = line.material_amount_total - line.allocated_budget_amt
            line.product_amt_na = total

    @api.depends('product_id', 'job_sheet_id.warehouse_id')
    def _comute_on_hand(self):
        for record in self:
            location_ids = []
            record.on_hand_qty = 0
            if record.product_id and record.job_sheet_id.warehouse_id:
                location_obj = self.env['stock.location']
                store_location_id = record.job_sheet_id.warehouse_id.view_location_id.id
                # addtional_ids = location_obj.search(
                #     [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                # for location in addtional_ids:
                #     if location.location_id.id not in addtional_ids.ids:
                #         location_ids.append(location.id)
                # convert above code to query
                self.env.cr.execute("""
                    SELECT id
                        FROM stock_location
                    WHERE location_id in (SELECT id FROM stock_location WHERE id = %s) AND usage = 'internal'
                """ % store_location_id)
                location_ids = [x[0] for x in self.env.cr.fetchall()]

                # child_location_ids = self.env['stock.location'].search(
                #     [('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                # convert above code to query
                self.env.cr.execute("""
                    SELECT id
                        FROM stock_location
                    WHERE id in (SELECT id FROM stock_location WHERE location_id in %s) AND id not in %s
                """ % (str(location_ids).replace('[', '(').replace(']', ')'),
                       str(location_ids).replace('[', '(').replace(']', ')')))
                child_location_ids = [x[0] for x in self.env.cr.fetchall()]
                final_location = child_location_ids + location_ids
                # stock_quant_ids = self.env['stock.quant'].search([('location_id', 'in', final_location), ('product_id', '=', record.product_id.id)])
                self.env.cr.execute("""
                    SELECT SUM(quantity)
                      FROM stock_quant
                    WHERE location_id in %s AND product_id = %s
                """ % (str(final_location).replace('[', '(').replace(']', ')'), record.product_id.id))
                qty = self.env.cr.fetchall()
                record.on_hand_qty = qty[0][0] or 0

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.product_qty = 1.0
            self.price_unit = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.product_qty = False
            self.price_unit = False

    @api.onchange('product_qty', 'price_unit')
    def onchange_quantity(self):
        price = 0.00
        for line in self:
            price = (line.product_qty * line.price_unit)
            line.material_amount_total = price

    @api.depends('product_qty', 'reserved_qty', 'purchased_qty')
    def _budget_quntity_left(self):
        total = 0
        for line in self:
            total = (line.product_qty - line.reserved_qty - line.purchased_qty - line.transferred_qty)
            line.budgeted_qty_left = total

    @api.depends('material_amount_total', 'reserved_amt', 'purchased_amt')
    def _budget_amount_left(self):
        total = 0
        for line in self:
            total = (line.material_amount_total - line.reserved_amt - line.purchased_amt - line.amount_return - line.transferred_amt)
            line.budgeted_amt_left = total

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                    'description': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self._origin.group_of_product._origin.id:
            if self._origin.group_of_product._origin.id != self.group_of_product.id:
                self.update({
                    'product_id': False,
                })
        else:
            self.update({
                'product_id': False,
            })


class MaterialGopLabour(models.Model):
    _name = 'material.gop.labour'
    _description = "Labour Gop"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    labour_gop_amount_total = fields.Float(string='Budgeted Amount')
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    reserved_amt = fields.Float('Reserved Budget Amount')
    transferred_amt = fields.Float('Transferred Amount')
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Amount', default=0.00)
    product_amt_na = fields.Float('Unallocated Amount', default=0.00, compute="_product_amt_na")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    labour_line_ids = fields.One2many('material.labour', 'labour_gop_id', string='Labour')
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

    @api.depends('job_sheet_id.material_labour_gop_ids', 'job_sheet_id.material_labour_gop_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.material_labour_gop_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('labour_gop_amount_total', 'actual_used_amt')
    def _unused_amt(self):
        total = 0
        for line in self:
            total = line.labour_gop_amount_total - line.actual_used_amt
            line.unused_amt = total

    @api.depends('labour_gop_amount_total', 'allocated_budget_amt')
    def _product_amt_na(self):
        total = 0
        for line in self:
            total = line.labour_gop_amount_total - line.allocated_budget_amt
            line.product_amt_na = total

    @api.depends('labour_gop_amount_total', 'reserved_amt', 'purchased_amt')
    def _budget_amount_left(self):
        total = 0
        for line in self:
            # total = (line.labour_gop_amount_total - line.reserved_amt - line.purchased_amt - line.amount_return)
            total = (line.labour_gop_amount_total - line.reserved_amt - line.actual_used_amt)
            line.budgeted_amt_left = total


class MaterialLabour(models.Model):
    _inherit = 'material.labour'
    _description = "Labour"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    purchased_qty = fields.Float('Purchased Quantity', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    billed_qty = fields.Float('Billed Quantity', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    reserved_qty = fields.Float('Reserved Budget Quantity')
    reserved_amt = fields.Float('Reserved Budget Amount')
    transferred_qty = fields.Float('Transferred Quantity')
    transferred_amt = fields.Float('Transferred Amount')
    received_qty = fields.Float('Received Quantity')
    budgeted_qty_left = fields.Float('Budgeted Quantity Left', compute="_budget_quntity_left")
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    unused_time = fields.Float('Unused Time', default=0.00, compute="_unused_time")
    actual_used_qty = fields.Float('Actual Used Quantity', default=0.00)
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    actual_used_time = fields.Float('Actual Used Time', default=0.00)
    allocated_budget_qty = fields.Float('Allocated Quantity', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Amount', default=0.00)
    allocated_budget_time = fields.Float('Allocated Time', default=0.00)
    allocated_contractors = fields.Integer('Allocated Contractors', default=0)
    unallocated_contractors = fields.Integer('Unallocated Contractors', default=0,
                                             compute="_compute_unallocated_contractors")
    unallocated_budget_time = fields.Float('Unallocated Time', default=0.00, compute="_compute_unallocated_time")
    product_qty_na = fields.Float('Unallocated Quantity', default=0.00, compute="_product_qty_na")
    product_amt_na = fields.Float('Unallocated Amount', default=0.00, compute="_product_amt_na")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    on_hand_qty = fields.Float('On Hand Quantity', default=0.00, compute="_comute_on_hand")
    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    labour_gop_id = fields.Many2one('material.gop.labour', string="Labour GOP ID", compute="_get_labour_gop_id")
    project_scope_id = fields.Many2one('project.scope.cost', string="Project Scope",
                                       compute="_get_project_scope_id", store=True)
    section_id = fields.Many2one('section.cost', string="Section",
                                 compute="_get_section_id", store=True)
    on_hand_qty_converted = fields.Float('On Hand Quantity', default=0.00,
                                         compute="_compute_on_hand_converted")
    amount_return = fields.Float('Return Amount', default=0.00)
    time = fields.Float('Budgeted Time', default=0.00)
    time_left = fields.Float('Budgeted Time Left', default=0.00, compute="_time_left")
    reserved_time = fields.Float('Reserved Budget Time', default=0.00, readonly=True)
    contractors = fields.Integer('Contractors', default=0)
    reserved_contractors = fields.Integer('Reserved Contractors', default=0)
    contractors_left = fields.Integer('Contractors Left', default=0, compute="_contractors_left")

    @api.depends('product_qty', 'price_unit')
    def compute_labour_amount_total(self):
        for line in self:
            if (line.reserved_contractors != 0 and line.reserved_time != 0) or line.actual_used_time != 0:
                current_contractors = line.contractors - line.reserved_contractors
                current_time = (line.time * line.contractors) - (
                            (line.reserved_time + line.actual_used_time) * line.reserved_contractors)
                current_amount_total = current_time * line.price_unit

                previous_unit_price = (line.reserved_amt + line.actual_used_amt + line.amount_return) / (
                            line.reserved_contractors * (line.reserved_time + line.actual_used_time))
                previous_amount_total = (line.reserved_contractors * (
                            line.reserved_time + line.actual_used_time)) * previous_unit_price
                line.labour_amount_total = current_amount_total + previous_amount_total
            else:
                line.labour_amount_total = line.contractors * line.time * line.price_unit

    @api.depends('contractors', 'reserved_contractors')
    def _contractors_left(self):
        total = 0
        for line in self:
            total = line.contractors - line.reserved_contractors
            line.contractors_left = total

    @api.depends('time')
    def _time_left(self):
        total = 0
        for line in self:
            total = line.time - line.reserved_time - line.actual_used_time
            line.time_left = total

    @api.depends('on_hand_qty', 'product_id', 'job_sheet_id.warehouse_id')
    def _compute_on_hand_converted(self):
        for rec in self:
            result_on_hand_qty = rec.on_hand_qty
            if rec.uom_id.category_id.name == 'Working Time':
                if rec.uom_id != rec.product_id.uom_id:
                    if rec.uom_id.name == 'Days':
                        result_on_hand_qty = rec.on_hand_qty / rec.project_id.working_hour_hours
                    elif rec.uom_id.name == 'Hours':
                        result_on_hand_qty = rec.on_hand_qty * rec.project_id.working_hour_hours
            rec.on_hand_qty_converted = result_on_hand_qty

    @api.depends('project_scope', 'section_name')
    def _get_section_id(self):
        for res in self:
            if res.project_scope:
                # section_line = self.env['section.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id),
                #      ('section_id', '=', res.section_name.id)], limit=1)
                # convert above code to filtered
                section_line = res.job_sheet_id.section_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id and p.section_id.id == res.section_name.id)

                if section_line:
                    res.section_id = section_line.id
                else:
                    res.section_id = False
            else:
                res.section_id = False

    @api.depends('project_scope')
    def _get_project_scope_id(self):
        for res in self:
            if res.project_scope:
                # scope_line = self.env['project.scope.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id)],
                #     limit=1)
                # convert above code to filtered
                scope_line = res.job_sheet_id.project_scope_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id)

                if scope_line:
                    res.project_scope_id = scope_line.id
                else:
                    res.project_scope_id = False
            else:
                res.project_scope_id = False

    @api.depends('project_scope', 'section_name', 'group_of_product')
    def _get_labour_gop_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product:
                # gop_line = self.env['material.gop.labour'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id)],
                #     limit=1)
                # convert above code to filtered
                gop_line = res.job_sheet_id.material_labour_gop_ids.filtered(
                    lambda p: p.project_scope.id == res.project_scope.id
                              and p.section_name.id == res.section_name.id
                              and p.group_of_product.id == res.group_of_product.id)
                if gop_line:
                    res.labour_gop_id = gop_line[0].id
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

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', 'in', ['product', 'service'])]}
            }

    @api.depends('job_sheet_id.material_labour_ids', 'job_sheet_id.material_labour_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.material_labour_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('product_qty', 'actual_used_qty')
    def _unused_qty(self):
        total = 0
        for line in self:
            total = line.product_qty - line.actual_used_qty
            line.unused_qty = total

    @api.depends('time', 'actual_used_time')
    def _unused_time(self):
        total = 0
        for line in self:
            total = line.time - line.actual_used_time
            line.unused_time = total

    @api.depends('labour_amount_total', 'actual_used_amt')
    def _unused_amt(self):
        total = 0
        for line in self:
            total = line.labour_amount_total - line.actual_used_amt
            line.unused_amt = total

    @api.depends('contractors', 'allocated_contractors')
    def _compute_unallocated_contractors(self):
        for rec in self:
            total = rec.contractors - rec.allocated_contractors
            rec.unallocated_contractors = total

    @api.depends('time', 'allocated_budget_time')
    def _compute_unallocated_time(self):
        for rec in self:
            total = rec.time - rec.allocated_budget_time
            rec.unallocated_budget_time = total

    @api.depends('product_qty', 'allocated_budget_qty')
    def _product_qty_na(self):
        total = 0
        for line in self:
            total = line.product_qty - line.allocated_budget_qty
            line.product_qty_na = total

    @api.depends('labour_amount_total', 'allocated_budget_amt')
    def _product_amt_na(self):
        total = 0
        for line in self:
            total = line.labour_amount_total - line.allocated_budget_amt
            line.product_amt_na = total

    @api.depends('product_id', 'job_sheet_id.warehouse_id')
    def _comute_on_hand(self):
        for record in self:
            location_ids = []
            record.on_hand_qty = 0
            if record.product_id and record.job_sheet_id.warehouse_id:
                location_obj = self.env['stock.location']
                store_location_id = record.job_sheet_id.warehouse_id.view_location_id.id
                # addtional_ids = location_obj.search(
                #     [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                # for location in addtional_ids:
                #     if location.location_id.id not in addtional_ids.ids:
                #         location_ids.append(location.id)
                # convert above code to query
                self.env.cr.execute("""
                    SELECT id
                        FROM stock_location
                    WHERE location_id in (SELECT id FROM stock_location WHERE id = %s) AND usage = 'internal'
                """ % store_location_id)
                location_ids = [x[0] for x in self.env.cr.fetchall()]

                # child_location_ids = self.env['stock.location'].search(
                #     [('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                # convert above code to query
                self.env.cr.execute("""
                    SELECT id
                        FROM stock_location
                    WHERE id in (SELECT id FROM stock_location WHERE location_id in %s) AND id not in %s
                """ % (str(location_ids).replace('[', '(').replace(']', ')'),
                       str(location_ids).replace('[', '(').replace(']', ')')))
                child_location_ids = [x[0] for x in self.env.cr.fetchall()]

                final_location = child_location_ids + location_ids
                # stock_quant_ids = self.env['stock.quant'].search([('location_id', 'in', final_location), ('product_id', '=', record.product_id.id)])
                self.env.cr.execute("""
                    SELECT SUM(quantity)
                      FROM stock_quant
                    WHERE location_id in %s AND product_id = %s
                """ % (str(final_location).replace('[', '(').replace(']', ')'), record.product_id.id))
                qty = self.env.cr.fetchall()
                record.on_hand_qty = qty[0][0] or 0

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                    'description': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self._origin.group_of_product._origin.id:
            if self._origin.group_of_product._origin.id != self.group_of_product.id:
                self.update({
                    'product_id': False,
                })
        else:
            self.update({
                'product_id': False,
            })

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.product_qty = 1.0
            self.price_unit = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.product_qty = False
            self.price_unit = False

    @api.onchange('product_qty', 'price_unit')
    def onchange_quantity(self):
        price = 0.00
        for line in self:
            price = (line.product_qty * line.price_unit)
            line.labour_amount_total = price

    @api.depends('product_qty', 'reserved_qty', 'purchased_qty')
    def _budget_quntity_left(self):
        total = 0
        for line in self:
            total = (line.product_qty - line.reserved_time - line.purchased_qty - line.transferred_qty)
            line.budgeted_qty_left = total

    @api.depends('labour_amount_total', 'reserved_amt', 'purchased_amt')
    def _budget_amount_left(self):
        total = 0
        for line in self:
            # total = (line.labour_amount_total - line.reserved_amt - line.purchased_amt - line.amount_return)
            total = (line.labour_amount_total - line.reserved_amt - line.actual_used_amt)
            line.budgeted_amt_left = total


class MaterialGopOverhead(models.Model):
    _name = 'material.gop.overhead'
    _description = "Overhead Gop"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    overhead_gop_amount_total = fields.Float(string='Budgeted Amount')
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    reserved_amt = fields.Float('Reserved Budget Amount')
    transferred_amt = fields.Float('Transferred Amount')
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Amount', default=0.00)
    product_amt_na = fields.Float('Unallocated Amount', default=0.00, compute="_product_amt_na")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    overhead_line_ids = fields.One2many('material.overhead', 'overhead_gop_id', string='Overhead')
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

    @api.depends('job_sheet_id.material_overhead_gop_ids', 'job_sheet_id.material_overhead_gop_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.material_overhead_gop_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('overhead_gop_amount_total', 'actual_used_amt')
    def _unused_amt(self):
        total = 0
        for line in self:
            total = line.overhead_gop_amount_total - line.actual_used_amt
            line.unused_amt = total

    @api.depends('overhead_gop_amount_total', 'allocated_budget_amt')
    def _product_amt_na(self):
        total = 0
        for line in self:
            total = line.overhead_gop_amount_total - line.allocated_budget_amt
            line.product_amt_na = total

    @api.depends('overhead_gop_amount_total', 'reserved_amt', 'purchased_amt')
    def _budget_amount_left(self):
        total = 0
        for line in self:
            total = (line.overhead_gop_amount_total - line.reserved_amt - line.purchased_amt - line.amount_return - line.transferred_amt)
            line.budgeted_amt_left = total


class MaterialOverhead(models.Model):
    _inherit = 'material.overhead'
    _description = "Overhead"
    _order = 'sequence,id'

    name = fields.Char('name', compute='_compute_name')
    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    purchased_qty = fields.Float('Purchased Quantity', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    billed_qty = fields.Float('Billed Quantity', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    reserved_qty = fields.Float('Reserved Budget Quantity')
    reserved_amt = fields.Float('Reserved Budget Amount')
    transferred_qty = fields.Float('Transferred Quantity')
    transferred_amt = fields.Float('Transferred Amount')
    received_qty = fields.Float('Received Quantity')
    budgeted_qty_left = fields.Float('Budgeted Quantity Left', compute="_budget_quntity_left")
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    actual_used_qty = fields.Float('Actual Used Quantity', default=0.00)
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    allocated_budget_qty = fields.Float('Allocated Quantity', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Amount', default=0.00)
    product_qty_na = fields.Float('Unallocated Quantity', default=0.00, compute="_product_qty_na")
    product_amt_na = fields.Float('Unallocated Amount', default=0.00, compute="_product_amt_na")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    on_hand_qty = fields.Float('On Hand Quantity', default=0.00, compute="_comute_on_hand")
    overhead_catagory = fields.Selection([
        ('product', 'Product'),
        ('petty cash', 'Petty Cash'),
        ('cash advance', 'Cash Advance'),
        ('fuel', 'Fuel'),
    ], string='Overhead Catagory', required=False)
    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    overhead_gop_id = fields.Many2one('material.gop.overhead', string="Ovehead GOP ID", compute="_get_overhead_gop_id")
    project_scope_id = fields.Many2one('project.scope.cost', string="Project Scope",
                                       compute="_get_project_scope_id", store=True)
    section_id = fields.Many2one('section.cost', string="Section",
                                 compute="_get_section_id", store=True)

    on_hand_qty_converted = fields.Float('On Hand Quantity', default=0.00,
                                         compute="_compute_on_hand_converted")
    amount_return = fields.Float('Return Amount', default=0.00)
    reserved_return_amount = fields.Float('Reserved Return Amount', default=0.00)
    over_amount = fields.Float('Over Amount', default=0.00)
    reserved_over_amount = fields.Float('Reserved Over Amount', default=0.00)
    po_reserved_qty = fields.Float('PO Reserved Quantity', default=0.00)

    @api.depends('product_qty', 'price_unit')
    def compute_overhead_amount_total(self):
        for line in self:
            if line.purchased_qty > 0 or (line.reserved_qty > 0 and line.reserved_amt) or (line.transferred_qty and line.transferred_amt):
                current_quantity = line.product_qty - line.reserved_qty - line.purchased_qty - line.transferred_qty
                current_amount_total = current_quantity * line.price_unit
                if line.reserved_qty > 0 >= line.po_reserved_qty:
                    previous_unit_price = ((line.reserved_amt + line.purchased_amt + line.amount_return
                                            + line.transferred_amt + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.reserved_qty + line.purchased_qty + line.transferred_qty))
                else:
                    previous_unit_price = ((line.reserved_amt + line.purchased_amt + line.amount_return
                                           + line.transferred_amt + line.reserved_return_amount
                                           - line.reserved_over_amount - line.over_amount ) /
                                           (line.po_reserved_qty + line.purchased_qty + line.transferred_qty))
                previous_amount_total = previous_unit_price * (line.purchased_qty + line.reserved_qty + line.transferred_qty)
                line.overhead_amount_total = current_amount_total + previous_amount_total
            else:
                line.overhead_amount_total = line.product_qty * line.price_unit

    @api.depends('on_hand_qty', 'product_id', 'job_sheet_id.warehouse_id')
    def _compute_on_hand_converted(self):
        for rec in self:
            result_on_hand_qty = rec.on_hand_qty
            if rec.uom_id.category_id.name == 'Working Time':
                if rec.uom_id != rec.product_id.uom_id:
                    if rec.uom_id.name == 'Days':
                        result_on_hand_qty = rec.on_hand_qty / rec.project_id.working_hour_hours
                    elif rec.uom_id.name == 'Hours':
                        result_on_hand_qty = rec.on_hand_qty * rec.project_id.working_hour_hours
            rec.on_hand_qty_converted = result_on_hand_qty

    @api.depends('project_scope', 'section_name')
    def _get_section_id(self):
        for res in self:
            if res.project_scope:
                # section_line = self.env['section.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id),
                #      ('section_id', '=', res.section_name.id)], limit=1)
                # convert above code to filtered
                section_line = res.job_sheet_id.section_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id and p.section_id.id == res.section_name.id)
                if section_line:
                    res.section_id = section_line.id
                else:
                    res.section_id = False
            else:
                res.section_id = False

    @api.depends('project_scope')
    def _get_project_scope_id(self):
        for res in self:
            if res.project_scope:
                # scope_line = self.env['project.scope.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id)],
                #     limit=1)
                # convert above code to filtered
                scope_line = res.job_sheet_id.project_scope_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id)
                if scope_line:
                    res.project_scope_id = scope_line.id
                else:
                    res.project_scope_id = False
            else:
                res.project_scope_id = False

    @api.depends('project_scope', 'section_name', 'group_of_product')
    def _get_overhead_gop_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product:
                # gop_line = self.env['material.gop.overhead'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id)],
                #     limit=1)
                # convert above code to filtered
                gop_line = res.job_sheet_id.material_overhead_gop_ids.filtered(
                    lambda p: p.project_scope.id == res.project_scope.id
                              and p.section_name.id == res.section_name.id
                              and p.group_of_product.id == res.group_of_product.id)
                if gop_line:
                    res.overhead_gop_id = gop_line[0].id
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

    @api.onchange('overhead_catagory', 'group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            if rec.overhead_catagory in ('product', 'fuel'):
                return {
                    'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'product')]}
                }
            else:
                return {
                    'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'consu')]}
                }

    @api.depends('name')
    def _compute_name(self):
        record = False
        for rec in self:
            scope = rec.project_scope.name
            section = rec.section_name.name
            variable = rec.variable_ref.name
            product = rec.product_id.name
            if rec.project_scope and rec.section_name and rec.variable_ref and rec.product_id:
                record = scope + ' - ' + section + ' - ' + variable + ' - ' + product
            elif rec.project_scope and rec.section_name and rec.product_id:
                record = scope + ' - ' + section + ' - ' + product
            rec.write({'name': record})
            # convert above code to query
            # self.env.cr.execute("""
            #     UPDATE material_overhead
            #     SET name = %s
            #     WHERE id = %s
            # """ % (record, rec.id))

    @api.depends('job_sheet_id.material_overhead_ids', 'job_sheet_id.material_overhead_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.material_overhead_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('product_qty', 'actual_used_qty')
    def _unused_qty(self):
        total = 0
        for line in self:
            total = line.product_qty - line.actual_used_qty
            line.unused_qty = total

    @api.depends('overhead_amount_total', 'actual_used_amt')
    def _unused_amt(self):
        total = 0
        for line in self:
            total = line.overhead_amount_total - line.actual_used_amt
            line.unused_amt = total

    @api.depends('product_qty', 'allocated_budget_qty')
    def _product_qty_na(self):
        total = 0
        for line in self:
            total = line.product_qty - line.allocated_budget_qty
            line.product_qty_na = total

    @api.depends('overhead_amount_total', 'allocated_budget_amt')
    def _product_amt_na(self):
        total = 0
        for line in self:
            total = line.overhead_amount_total - line.allocated_budget_amt
            line.product_amt_na = total

    @api.depends('product_id', 'job_sheet_id.warehouse_id')
    def _comute_on_hand(self):
        for record in self:
            location_ids = []
            record.on_hand_qty = 0
            if record.product_id and record.job_sheet_id.warehouse_id:
                location_obj = self.env['stock.location']
                store_location_id = record.job_sheet_id.warehouse_id.view_location_id.id
                # addtional_ids = location_obj.search(
                #     [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                # for location in addtional_ids:
                #     if location.location_id.id not in addtional_ids.ids:
                #         location_ids.append(location.id)
                # conver above code to query
                self.env.cr.execute("""
                    SELECT id
                        FROM stock_location
                    WHERE location_id in (SELECT id FROM stock_location WHERE id = %s) AND usage = 'internal'
                """ % store_location_id)
                location_ids = [x[0] for x in self.env.cr.fetchall()]

                # child_location_ids = self.env['stock.location'].search(
                #     [('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                # convert above code to query
                self.env.cr.execute("""
                    SELECT id
                        FROM stock_location
                    WHERE id in (SELECT id FROM stock_location WHERE location_id in %s) AND id not in %s
                """ % (str(location_ids).replace('[', '(').replace(']', ')'),
                       str(location_ids).replace('[', '(').replace(']', ')')))
                child_location_ids = [x[0] for x in self.env.cr.fetchall()]
                final_location = child_location_ids + location_ids
                # stock_quant_ids = self.env['stock.quant'].search([('location_id', 'in', final_location), ('product_id', '=', record.product_id.id)])
                self.env.cr.execute("""
                    SELECT SUM(quantity)
                      FROM stock_quant
                    WHERE location_id in %s AND product_id = %s
                """ % (str(final_location).replace('[', '(').replace(']', ')'), record.product_id.id))
                qty = self.env.cr.fetchall()
                record.on_hand_qty = qty[0][0] or 0

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                    'description': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self._origin.group_of_product._origin.id:
            if self._origin.group_of_product._origin.id != self.group_of_product.id:
                self.update({
                    'product_id': False,
                })
        else:
            self.update({
                'product_id': False,
            })

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.product_qty = 1.0
            self.price_unit = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.product_qty = False
            self.price_unit = False

    @api.onchange('product_qty', 'price_unit')
    def onchange_quantity(self):
        price = 0.00
        for line in self:
            price = (line.product_qty * line.price_unit)
            line.overhead_amount_total = price

    @api.depends('product_qty', 'reserved_qty', 'purchased_qty')
    def _budget_quntity_left(self):
        total = 0
        for line in self:
            total = (line.product_qty - line.reserved_qty - line.purchased_qty - line.transferred_qty)
            line.budgeted_qty_left = total

    @api.depends('overhead_amount_total', 'reserved_amt', 'purchased_amt')
    def _budget_amount_left(self):
        total = 0
        for line in self:
            total = (line.overhead_amount_total - line.reserved_amt - line.purchased_amt - line.amount_return - line.transferred_amt)
            line.budgeted_amt_left = total


class MaterialGopSubcon(models.Model):
    _name = 'material.gop.subcon'
    _description = "Subcon Gop"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    subcon_gop_amount_total = fields.Float(string='Budgeted Amount')
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    reserved_amt = fields.Float('Reserved Budget Amount')
    transferred_amt = fields.Float('Transferred Amount')
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Amount', default=0.00)
    product_amt_na = fields.Float('Unallocated Amount', default=0.00, compute="_product_amt_na")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
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

    @api.depends('job_sheet_id.material_subcon_gop_ids', 'job_sheet_id.material_subcon_gop_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.material_subcon_gop_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('subcon_gop_amount_total', 'actual_used_amt')
    def _unused_amt(self):
        total = 0
        for line in self:
            total = line.subcon_gop_amount_total - line.actual_used_amt
            line.unused_amt = total

    @api.depends('subcon_gop_amount_total', 'allocated_budget_amt')
    def _product_amt_na(self):
        total = 0
        for line in self:
            total = line.subcon_gop_amount_total - line.allocated_budget_amt
            line.product_amt_na = total

    @api.depends('subcon_gop_amount_total', 'reserved_amt', 'purchased_amt')
    def _budget_amount_left(self):
        total = 0
        for line in self:
            total = (line.subcon_gop_amount_total - line.reserved_amt - line.purchased_amt - line.amount_return)
            line.budgeted_amt_left = total


class MaterialSubcon(models.Model):
    _name = 'material.subcon'
    _description = "Subcon"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    description = fields.Char(string='Description')
    product_qty = fields.Float(string='Budgeted Quantity', default='0.00')
    price_unit = fields.Float(string='Unit Price', default='0.00')
    subcon_amount_total = fields.Float(string='Budgeted Amount', compute='_compute_amount_total')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    variable = fields.Many2one('variable.template', string='Job Subcon',
                               domain="[('variable_subcon', '=', True), ('company_id', '=', parent.company_id)]")
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    purchased_qty = fields.Float('Purchased Quantity', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    billed_qty = fields.Float('Billed Quantity', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    reserved_qty = fields.Float('Reserved Budget Quantity')
    reserved_amt = fields.Float('Reserved Budget Amount')
    budgeted_qty_left = fields.Float('Budgeted Quantity Left', compute="_budget_quntity_left")
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    actual_used_qty = fields.Float('Actual Used Quantity', default=0.00)
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    allocated_budget_qty = fields.Float('Allocated Quantity', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Amount', default=0.00)
    product_qty_na = fields.Float('Unallocated Quantity', default=0.00, compute="_product_qty_na")
    product_amt_na = fields.Float('Unallocated Amount', default=0.00, compute="_product_amt_na")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_id = fields.Many2one('project.scope.cost', string="Project Scope",
                                       compute="_get_project_scope_id", store=True)
    section_id = fields.Many2one('section.cost', string="Section",
                                 compute="_get_section_id", store=True)
    amount_return = fields.Float('Return Amount', default=0.00)
    reserved_return_amount = fields.Float('Reserved Return Amount', default=0.00)
    over_amount = fields.Float('Over Amount', default=0.00)
    reserved_over_amount = fields.Float('Reserved Over Amount', default=0.00)
    po_reserved_qty = fields.Float('PO Reserved Quantity', default=0.00)

    @api.depends('project_scope', 'section_name')
    def _get_section_id(self):
        for res in self:
            if res.project_scope:
                # section_line = self.env['section.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id),
                #      ('section_id', '=', res.section_name.id)], limit=1)
                # convert above code to filtered
                section_line = res.job_sheet_id.section_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id and p.section_id.id == res.section_name.id)
                if section_line:
                    res.section_id = section_line.id
                else:
                    res.section_id = False
            else:
                res.section_id = False

    @api.depends('project_scope')
    def _get_project_scope_id(self):
        for res in self:
            if res.project_scope:
                # scope_line = self.env['project.scope.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id)],
                #     limit=1)
                # convert above code to filtered
                scope_line = res.job_sheet_id.project_scope_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id)
                if scope_line:
                    res.project_scope_id = scope_line.id
                else:
                    res.project_scope_id = False
            else:
                res.project_scope_id = False

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

    @api.depends('job_sheet_id.material_subcon_ids', 'job_sheet_id.material_subcon_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.material_subcon_ids:
                no += 1
                l.sr_no = no

    def _compute_amount_total(self):
        for line in self:
            if line.purchased_qty > 0 or (line.reserved_qty > 0 and line.reserved_amt):
                current_quantity = line.product_qty - line.reserved_qty - line.purchased_qty
                current_amount_total = current_quantity * line.price_unit
                if line.reserved_qty > 0 >= line.po_reserved_qty:
                    previous_unit_price = ((line.reserved_amt + line.purchased_amt + line.amount_return
                                            + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.reserved_qty + line.purchased_qty ))
                else:
                    previous_unit_price = ((line.reserved_amt + line.purchased_amt + line.amount_return
                                            + line.reserved_return_amount
                                           - line.reserved_over_amount - line.over_amount ) /
                                           (line.po_reserved_qty + line.purchased_qty))
                previous_amount_total = previous_unit_price * (line.purchased_qty + line.reserved_qty)
                line.subcon_amount_total = current_amount_total + previous_amount_total
            else:
                line.subcon_amount_total = line.product_qty * line.price_unit

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('product_qty', 'actual_used_qty')
    def _unused_qty(self):
        total = 0
        for line in self:
            total = line.product_qty - line.actual_used_qty
            line.unused_qty = total

    @api.depends('subcon_amount_total', 'actual_used_amt')
    def _unused_amt(self):
        total = 0
        for line in self:
            total = line.subcon_amount_total - line.actual_used_amt
            line.unused_amt = total

    @api.depends('product_qty', 'allocated_budget_qty')
    def _product_qty_na(self):
        total = 0
        for line in self:
            total = line.product_qty - line.allocated_budget_qty
            line.product_qty_na = total

    @api.depends('subcon_amount_total', 'allocated_budget_amt')
    def _product_amt_na(self):
        total = 0
        for line in self:
            total = line.subcon_amount_total - line.allocated_budget_amt
            line.product_amt_na = total

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable': False,
                    'description': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable': False,
                })
        else:
            self.update({
                'variable': False,
            })

    @api.onchange('variable')
    def onchange_variable(self):
        if self.variable:
            self.uom_id = self.variable.variable_uom.id
            self.product_qty = 1.0
            self.price_unit = self.variable.total_variable
            self.description = self.variable.name
        else:
            self.description = False
            self.uom_id = False
            self.product_qty = False
            self.price_unit = False

    @api.onchange('product_qty', 'price_unit')
    def onchange_quantity(self):
        price = 0.00
        for line in self:
            price = (line.product_qty * line.price_unit)
            line.subcon_amount_total = price

    @api.depends('product_qty', 'reserved_qty', 'purchased_qty')
    def _budget_quntity_left(self):
        total = 0
        for line in self:
            total = (line.product_qty - line.reserved_qty - line.purchased_qty)
            line.budgeted_qty_left = total

    @api.depends('subcon_amount_total', 'reserved_amt', 'purchased_amt')
    def _budget_amount_left(self):
        total = 0
        for line in self:
            total = (line.subcon_amount_total - line.reserved_amt - line.purchased_amt - line.amount_return)
            line.budgeted_amt_left = total


# ------ object 'Internal Asset' ------------
class InternalAsset(models.Model):
    _name = 'internal.asset'
    _description = "Asset"
    _order = 'sequence,id'

    name = fields.Char('name', compute='_compute_name')
    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope_line_id = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_id = fields.Many2one('variable.template', string='Variable')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category', required=True)
    asset_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    description = fields.Text(string="Description")
    budgeted_qty = fields.Float('Budgeted Quantity', default=0.00, required=True)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    price_unit = fields.Float(string='Unit Price', default=0.00, required=True)
    budgeted_amt = fields.Float('Budgeted Amount', compute='_compute_budgeted_amt')
    budgeted_qty_left = fields.Float('Budgeted Quantity Left', compute="_budget_quntity_left")
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    actual_used_qty = fields.Float('Actual Used Quantity', default=0.00)
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    allocated_budget_qty = fields.Float('Allocated Quantity', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Amount', default=0.00)
    unallocated_budget_qty = fields.Float('Unallocated Quantity', default=0.00,
                                          compute="_unallocated_budget_qty")
    unallocated_amt = fields.Float('Unallocated Amount', default=0.00, compute="_unallocated_amt")
    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_id = fields.Many2one('project.scope.cost', string="Project Scope",
                                       compute="_get_project_scope_id", store=True)
    section_id = fields.Many2one('section.cost', string="Section",
                                 compute="_get_section_id", store=True)

    @api.depends('budgeted_qty', 'price_unit')
    def _compute_budgeted_amt(self):
        for rec in self:
            if rec.actual_used_amt != 0:
                current_quantity = rec.budgeted_qty - rec.actual_used_qty
                current_amount_total = current_quantity * rec.price_unit
                previous_unit_price = rec.actual_used_amt / rec.actual_used_qty
                previous_amount_total = previous_unit_price * rec.actual_used_qty
                rec.budgeted_amt = current_amount_total + previous_amount_total
            else:
                rec.budgeted_amt = rec.budgeted_qty * rec.price_unit

    @api.depends('project_scope', 'section_name')
    def _get_section_id(self):
        for res in self:
            if res.project_scope:
                # section_line = self.env['section.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id),
                #      ('section_id', '=', res.section_name.id)], limit=1)
                # convert above code to filtered
                section_line = res.job_sheet_id.section_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id and p.section_id.id == res.section_name.id)
                if section_line:
                    res.section_id = section_line.id
                else:
                    res.section_id = False
            else:
                res.section_id = False

    @api.depends('project_scope')
    def _get_project_scope_id(self):
        for res in self:
            if res.project_scope:
                # scope_line = self.env['project.scope.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id)],
                #     limit=1)
                # convert above code to filtered
                scope_line = res.job_sheet_id.project_scope_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id)
                if scope_line:
                    res.project_scope_id = scope_line.id
                else:
                    res.project_scope_id = False
            else:
                res.project_scope_id = False

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
        for rec in self:
            scope = rec.project_scope.name
            section = rec.section_name.name
            variable = rec.variable_id.name
            asset = rec.asset_id.name
            if rec.project_scope and rec.section_name and rec.variable_id and rec.asset_id:
                record = scope + ' - ' + section + ' - ' + variable + ' - ' + asset
            elif rec.project_scope and rec.section_name and rec.asset_id:
                record = scope + ' - ' + section + ' - ' + asset
            else:
                record = asset
            rec.write({'name': record})
            # convert above code to query
            # self.env.cr.execute("""
            #     UPDATE internal_asset
            #     SET name = %s
            #     WHERE id = %s
            # """ % (record, rec.id))

    @api.depends('job_sheet_id.internal_asset_ids', 'job_sheet_id.internal_asset_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.internal_asset_ids:
                no += 1
                l.sr_no = no

    @api.onchange('asset_category_id')
    def onchange_asset_category(self):
        if self.asset_category_id:
            asset = self.env['maintenance.equipment'].sudo().search(
                [('category_id.id', '=', self.asset_category_id.id)])
            return {'domain': {'asset_id': [('id', 'in', asset.ids)]}}

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'asset_category_id': False,
                    'asset_id': False,
                    'description': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'asset_category_id': False,
                'asset_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'asset_category_id': False,
                    'asset_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'asset_category_id': False,
                'asset_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'asset_category_id': False,
                    'asset_id': False,
                })
        else:
            self.update({
                'asset_category_id': False,
                'asset_id': False,
            })

    @api.onchange('asset_category_id')
    def _onchange_asset_category_id_handling(self):
        if self._origin.asset_category_id._origin.id:
            if self._origin.asset_category_id._origin.id != self.asset_category_id.id:
                self.update({
                    'asset_id': False,
                })
        else:
            self.update({
                'asset_id': False,
            })

    @api.onchange('asset_id')
    def onchange_asset_id(self):
        if self.asset_id:
            self.budgeted_qty = 1.0
            self.description = self.asset_id.display_name
        else:
            self.budgeted_qty = 1.0
            self.description = False

    @api.onchange('budgeted_qty', 'price_unit')
    def onchange_quantity(self):
        price = 0.00
        for line in self:
            price = (line.budgeted_qty * line.price_unit)
            line.budgeted_amt = price

    @api.depends('budgeted_qty', 'actual_used_qty')
    def _budget_quntity_left(self):
        total = 0
        for line in self:
            total = (line.budgeted_qty - line.actual_used_qty)
            line.budgeted_qty_left = total

    @api.depends('budgeted_amt', 'actual_used_amt')
    def _budget_amount_left(self):
        total = 0
        for res in self:
            total = res.budgeted_amt - res.actual_used_amt
            res.budgeted_amt_left = total

    @api.depends('budgeted_qty', 'actual_used_qty')
    def _unused_qty(self):
        total = 0
        for line in self:
            total = line.budgeted_qty - line.actual_used_qty
            line.unused_qty = total

    @api.depends('budgeted_amt', 'actual_used_amt')
    def _unused_amt(self):
        total = 0
        for line in self:
            total = line.budgeted_amt - line.actual_used_amt
            line.unused_amt = total

    @api.depends('budgeted_qty', 'allocated_budget_qty')
    def _unallocated_budget_qty(self):
        total = 0
        for res in self:
            total = res.budgeted_qty - res.allocated_budget_qty
            res.unallocated_budget_qty = total

    @api.depends('budgeted_amt', 'allocated_budget_amt')
    def _unallocated_amt(self):
        total = 0
        for res in self:
            total = res.budgeted_amt - res.allocated_budget_amt
            res.unallocated_amt = total

    @api.onchange('asset_id')
    def _onchange_uom_asset_id(self):
        for rec in self:
            domain = self.env['uom.category'].search([('name', '=', 'Working Time')], limit=1)
            if rec.asset_id:
                if domain:
                    return {
                        'domain': {'uom_id': [('category_id', '=', domain.id)]}
                    }
                else:
                    return {
                        'domain': {'uom_id': []}
                    }
            else:
                return {
                    'domain': {'uom_id': []}
                }


class MaterialGopEquipment(models.Model):
    _name = 'material.gop.equipment'
    _description = "Equipment Gop"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    equipment_gop_amount_total = fields.Float(string='Budgeted Amount')
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    reserved_amt = fields.Float('Reserved Budget Amount')
    transferred_amt = fields.Float('Transferred Amount')
    received_qty = fields.Float('Received Quantity')
    returned_qty = fields.Float('Returned Quantity')
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Amount', default=0.00)
    product_amt_na = fields.Float('Unallocated Amount', default=0.00, compute="_product_amt_na")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    equipment_line_ids = fields.One2many('material.equipment', 'equipment_gop_id', string='Equipment')
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

    @api.depends('job_sheet_id.material_equipment_gop_ids', 'job_sheet_id.material_equipment_gop_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.material_equipment_gop_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('equipment_gop_amount_total', 'actual_used_amt')
    def _unused_amt(self):
        total = 0
        for line in self:
            total = line.equipment_gop_amount_total - line.actual_used_amt
            line.unused_amt = total

    @api.depends('equipment_gop_amount_total', 'allocated_budget_amt')
    def _product_amt_na(self):
        total = 0
        for line in self:
            total = line.equipment_gop_amount_total - line.allocated_budget_amt
            line.product_amt_na = total

    @api.depends('equipment_gop_amount_total', 'reserved_amt', 'purchased_amt')
    def _budget_amount_left(self):
        total = 0
        for line in self:
            total = (line.equipment_gop_amount_total - line.reserved_amt - line.purchased_amt - line.amount_return)
            line.budgeted_amt_left = total


class MaterialEquipment(models.Model):
    _name = 'material.equipment'
    _description = "Equipment"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    description = fields.Char(string='Description')
    product_qty = fields.Float(string='Budgeted Quantity', default='0.00')
    price_unit = fields.Float(string='Unit Price', default='0.00')
    equipment_amount_total = fields.Float(string='Budgeted Amount', compute='_compute_equipment_amount_total')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    purchased_qty = fields.Float('Purchased Quantity', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    billed_qty = fields.Float('Billed Quantity', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    reserved_qty = fields.Float('Reserved Budget Quantity')
    reserved_amt = fields.Float('Reserved Budget Amount')
    budgeted_qty_left = fields.Float('Budgeted Quantity Left', compute="_budget_quntity_left")
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    received_qty = fields.Float('Received Quantity')
    returned_qty = fields.Float('Returned Quantity')
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    actual_used_qty = fields.Float('Actual Used Quantity', default=0.00)
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    allocated_budget_qty = fields.Float('Allocated Quantity', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Amount', default=0.00)
    product_qty_na = fields.Float('Unallocated Quantity', default=0.00, compute="_product_qty_na")
    product_amt_na = fields.Float('Unallocated Amount', default=0.00, compute="_product_amt_na")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    equipment_gop_id = fields.Many2one('material.gop.equipment', string="Equipment GOP ID",
                                       compute="_get_equipment_gop_id")
    project_scope_id = fields.Many2one('project.scope.cost', string="Project Scope",
                                       compute="_get_project_scope_id", store=True)
    section_id = fields.Many2one('section.cost', string="Section",
                                 compute="_get_section_id", store=True)
    amount_return = fields.Float('Return Amount', default=0.00)
    reserved_return_amount = fields.Float('Reserved Return Amount', default=0.00)
    over_amount = fields.Float('Over Amount', default=0.00)
    reserved_over_amount = fields.Float('Reserved Over Amount', default=0.00)
    po_reserved_qty = fields.Float('PO Reserved Quantity', default=0.00)

    @api.depends('product_qty', 'price_unit')
    def _compute_equipment_amount_total(self):
        for line in self:
            if line.purchased_qty > 0 or (line.reserved_qty > 0 and line.reserved_amt):
                current_quantity = line.product_qty - line.reserved_qty - line.purchased_qty
                current_amount_total = current_quantity * line.price_unit
                if line.reserved_qty > 0 >= line.po_reserved_qty:
                    previous_unit_price = ((line.reserved_amt + line.purchased_amt + line.amount_return
                                            + line.reserved_return_amount
                                            - line.reserved_over_amount - line.over_amount) /
                                           (line.reserved_qty + line.purchased_qty))
                else:
                    previous_unit_price = ((line.reserved_amt + line.purchased_amt + line.amount_return
                                           + line.reserved_return_amount
                                           - line.reserved_over_amount - line.over_amount ) /
                                           (line.po_reserved_qty + line.purchased_qty))
                previous_amount_total = previous_unit_price * (line.purchased_qty + line.reserved_qty)
                line.equipment_amount_total = current_amount_total + previous_amount_total
            else:
                line.equipment_amount_total = line.product_qty * line.price_unit

    @api.depends('project_scope', 'section_name')
    def _get_section_id(self):
        for res in self:
            if res.project_scope:
                # section_line = self.env['section.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id),
                #      ('section_id', '=', res.section_name.id)], limit=1)
                # convert above code to filtered
                section_line = res.job_sheet_id.section_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id and p.section_id.id == res.section_name.id)
                if section_line:
                    res.section_id = section_line.id
                else:
                    res.section_id = False
            else:
                res.section_id = False

    @api.depends('project_scope')
    def _get_project_scope_id(self):
        for res in self:
            if res.project_scope:
                # scope_line = self.env['project.scope.cost'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope_id', '=', res.project_scope.id)],
                #     limit=1)
                # convert above code to filtered
                scope_line = res.job_sheet_id.project_scope_cost_ids.filtered(
                    lambda p: p.project_scope_id.id == res.project_scope.id)
                if scope_line:
                    res.project_scope_id = scope_line.id
                else:
                    res.project_scope_id = False
            else:
                res.project_scope_id = False

    @api.depends('project_scope', 'section_name', 'group_of_product')
    def _get_equipment_gop_id(self):
        for res in self:
            if res.project_scope and res.section_name and res.group_of_product:
                # gop_line = self.env['material.gop.equipment'].search(
                #     [('job_sheet_id', '=', res.job_sheet_id.id), ('project_scope', '=', res.project_scope.id),
                #      ('section_name', '=', res.section_name.id), ('group_of_product', '=', res.group_of_product.id)],
                #     limit=1)
                # convert above code to filtered
                gop_line = res.job_sheet_id.material_equipment_gop_ids.filtered(
                    lambda
                        p: p.project_scope.id == res.project_scope.id and p.section_name.id == res.section_name.id and
                           p.group_of_product.id == res.group_of_product.id)
                if gop_line:
                    res.equipment_gop_id = gop_line[0].id
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

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'asset')]}
            }

    @api.depends('job_sheet_id.material_equipment_ids', 'job_sheet_id.material_equipment_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.material_equipment_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('product_qty', 'actual_used_qty')
    def _unused_qty(self):
        total = 0
        for line in self:
            total = line.product_qty - line.actual_used_qty
            line.unused_qty = total

    @api.depends('equipment_amount_total', 'actual_used_amt')
    def _unused_amt(self):
        total = 0
        for line in self:
            total = line.equipment_amount_total - line.actual_used_amt
            line.unused_amt = total

    @api.depends('product_qty', 'allocated_budget_qty')
    def _product_qty_na(self):
        total = 0
        for line in self:
            total = line.product_qty - line.allocated_budget_qty
            line.product_qty_na = total

    @api.depends('equipment_amount_total', 'allocated_budget_amt')
    def _product_amt_na(self):
        total = 0
        for line in self:
            total = line.equipment_amount_total - line.allocated_budget_amt
            line.product_amt_na = total

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                    'description': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self._origin.group_of_product._origin.id:
            if self._origin.group_of_product._origin.id != self.group_of_product.id:
                self.update({
                    'product_id': False,
                })
        else:
            self.update({
                'product_id': False,
            })

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.product_qty = 1.0
            self.price_unit = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.product_qty = False
            self.price_unit = False

    @api.onchange('product_qty', 'price_unit')
    def onchange_quantity(self):
        price = 0.00
        for line in self:
            price = (line.product_qty * line.price_unit)
            line.equipment_amount_total = price

    @api.depends('product_qty', 'reserved_qty', 'purchased_qty')
    def _budget_quntity_left(self):
        total = 0
        for line in self:
            total = (line.product_qty - line.reserved_qty - line.purchased_qty)
            line.budgeted_qty_left = total

    @api.depends('equipment_amount_total', 'reserved_amt', 'purchased_amt')
    def _budget_amount_left(self):
        total = 0
        for line in self:
            total = (line.equipment_amount_total - line.reserved_amt - line.purchased_amt - line.amount_return)
            line.budgeted_amt_left = total


class ContractHistory(models.Model):
    _name = 'contract.history'
    _description = "Contract History"
    _order = 'sequence'
    _check_company_auto = True

    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    contract_history = fields.Many2one('sale.order.const', string="Contract History")
    job_reference = fields.Many2many('job.estimate', string="BOQ")
    job_estimate = fields.Many2one('job.estimate', string="BOQ")
    date_order = fields.Datetime(string="Order Date")
    subtotal = fields.Float(string="Budgeted Amount")
    contract_category = fields.Selection([
        ('main', 'Main Contract'),
        ('var', 'Variation Order')
    ], string='Category', default='main')
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', readonly=True)
    created_by = fields.Many2one('res.users', string='Created By')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    currency_id = fields.Many2one(related='job_sheet_id.currency_id', string="Currency")
    company_currency_id = fields.Many2one('res.currency', string='Currency')
    state = fields.Selection([('in_progress', 'In Progress'), ('done', 'Done'), ('cancel', 'Cancelled')],
                             string='Status')
    approved_date = fields.Datetime('Approved Date')
    department_type = fields.Selection(related='job_sheet_id.department_type', string='Type of Department')
    total_variation_order = fields.Monetary(related='contract_history.total_variation_order')
    total_variation_order_material = fields.Monetary(related='contract_history.total_variation_order_material')
    total_variation_order_labour = fields.Monetary(related='contract_history.total_variation_order_labour')
    total_variation_order_overhead = fields.Monetary(related='contract_history.total_variation_order_overhead')
    total_variation_order_equipment = fields.Monetary(related='contract_history.total_variation_order_equipment')
    total_variation_order_asset = fields.Monetary(related='contract_history.total_variation_order_asset')
    total_variation_order_subcon = fields.Monetary(related='contract_history.total_variation_order_subcon')
    adjustment_sub = fields.Float(string="Adjustment (+)", related='contract_history.adjustment_sub')
    discount_sub = fields.Float(string="Discount (-)", related='contract_history.discount_sub')
    
    updated_variation_order_history_ids = fields.One2many('variation.order.history', 'contract_history_id',
                                                          string="Updated Variation Order History",
                                                          domain=[('history_category', '=', 'is_updated')])
    added_variation_order_history_ids = fields.One2many('variation.order.history', 'contract_history_id',
                                                        string="Added Variation Order History",
                                                        domain=[('history_category', '=', 'is_added')])
    removed_variation_order_history_ids = fields.One2many('variation.order.history', 'contract_history_id',
                                                          string="Removed Variation Order History",
                                                          domain=[('history_category', '=', 'is_removed')])
    is_updated_subcon_exist = fields.Boolean('Is Subcon Exist')
    is_added_subcon_exist = fields.Boolean('Is Subcon Exist')
    is_removed_subcon_exist = fields.Boolean('Is Subcon Exist')
    is_updated_asset_exist = fields.Boolean('Is Asset Exist')
    is_added_asset_exist = fields.Boolean('Is Asset Exist')
    is_removed_asset_exist = fields.Boolean('Is Asset Exist')

    @api.depends('job_sheet_id.contract_history_ids', 'job_sheet_id.contract_history_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.contract_history_ids:
                no += 1
                l.sr_no = no


class VariationOrderHistory(models.Model):
    _name = 'variation.order.history'
    _description = "Variation Order History"

    contract_history_id = fields.Many2one('contract.history', string="Cost Sheet", ondelete='cascade')
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    history_category = fields.Selection([('is_added', 'Added'),
                                         ('is_updated', 'Updated'),
                                         ('is_removed', 'Removed')],
                                        string="History Category")
    project_scope_id = fields.Many2one('project.scope.line', string='Project Scope')
    section_id = fields.Many2one('section.line', string='Section')
    group_of_product_id = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    subcon_id = fields.Many2one('variable.template', string='Subcon')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    quantity_before = fields.Float('Quantity Before', default=0.00)
    quantity_after = fields.Float('Quantity After', default=0.00)
    unit_price_before = fields.Float('Unit Price Before', default=0.00)
    unit_price_after = fields.Float('Unit Price After', default=0.00)
    contractors_before = fields.Integer('Contractors Before', )
    contractors_after = fields.Integer('Contractors After', )
    time_before = fields.Float('Time Before', default=0.00)
    time_after = fields.Float('Time After', default=0.00)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    currency_id = fields.Many2one(related='contract_history_id.currency_id', string="Currency")
    subtotal = fields.Float('Subtotal', default=0.00)

    @api.depends('contract_history_id.updated_variation_order_history_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            # line.sr_no = no
            for l in line.contract_history_id.updated_variation_order_history_ids:
                no += 1
                l.sr_no = no
            no = 0
            # line.sr_no = no
            for l in line.contract_history_id.added_variation_order_history_ids:
                no += 1
                l.sr_no = no
            no = 0
            # line.sr_no = no
            for l in line.contract_history_id.removed_variation_order_history_ids:
                no += 1
                l.sr_no = no


class CostSheetApprovalMatrixLine(models.Model):
    _name = 'cost.sheet.approval.matrix.line'
    _description = 'Approval Matrix Table For Cost Sheet'

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
    cost_sheet_id = fields.Many2one('job.cost.sheet', string='Cost Sheet')


class InternalTransferBudget(models.Model):
    _name = 'internal.transfer.budget.line'
    _description = "Budget Change Request"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    type = fields.Selection([('material', 'Material'),
                             ('labour', 'Labour'),
                             ('overhead', 'Overhead'),
                             ('equipment', 'Equipment'),
                             ('internal_asset', 'Internal Asset'),
                             ('subcon', 'Subcon')],
                            string="Type")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope',
                                    domain="[('project_id','=', parent.project_id)]")
    section_name = fields.Many2one('section.line', string='Section',
                                   domain="[('project_scope','=', project_scope), ('project_id','=', parent.project_id)]")
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
    adj_unit_price = fields.Float('Adjusted unit price', default=0.00)
    cur_amt = fields.Float('Current amount', default=0.00)
    adj_amt = fields.Float('Adjusted amount', default=0.00)
    adjusted = fields.Float('Adjusted', default=0.00)
    is_newly_added_product = fields.Boolean('Is newly added product')
    is_not_from_cost_sheet = fields.Boolean('Is not from cost sheet')

    @api.depends('job_sheet_id.internal_transfer_budget_line_ids',
                 'job_sheet_id.internal_transfer_budget_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.internal_transfer_budget_line_ids:
                no += 1
                l.sr_no = no


class InternalTransferBudgetHistory(models.Model):
    _name = 'internal.transfer.budget.history'
    _description = "Budget Change Request History"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
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

    @api.depends('job_sheet_id.history_itb_ids', 'job_sheet_id.history_itb_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.history_itb_ids:
                no += 1
                l.sr_no = no


class ProjectBudgetTransfer(models.Model):
    _name = 'project.budget.transfer.line'
    _description = "Project Budget Transfer"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    type = fields.Selection([('material', 'Material'),
                             ('labour', 'Labour'),
                             ('overhead', 'Overhead'),
                             ('equipment', 'Equipment'),
                             ('subcon', 'Subcon')],
                            string="Type")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope',
                                    domain="[('project_id','=', parent.project_id)]")
    section_name = fields.Many2one('section.line', string='Section',
                                   domain="[('project_scope','=', project_scope), ('project_id','=', parent.project_id)]")
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

    @api.depends('job_sheet_id.project_budget_transfer_line_ids',
                 'job_sheet_id.project_budget_transfer_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.project_budget_transfer_line_ids:
                no += 1
                l.sr_no = no


class InternalTransferBudgetHistory(models.Model):
    _name = 'project.budget.transfer.history'
    _description = "Project Budget Transfer History"
    _order = 'sequence'

    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    date = fields.Datetime(string="Change Date")
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    project_id = fields.Many2one('project.project', string='From Project')
    dest_project_id = fields.Many2one('project.project', string='To Project')
    pbt_id = fields.Many2one('internal.transfer.budget', string='Project Budget Transfer Id')
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

    @api.depends('job_sheet_id.history_pbt_ids', 'job_sheet_id.history_pbt_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.history_pbt_ids:
                no += 1
                l.sr_no = no


class ChangeAllocationLineCost(models.Model):
    _name = 'change.allocation.line.cost'
    _description = "Change Allocation"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    type = fields.Selection([('material', 'Material'),
                             ('labour', 'Labour'),
                             ('overhead', 'Overhead'),
                             ('equipment', 'Equipment'),
                             ('internal_asset', 'Internal Asset'),
                             ('subcon', 'Subcon')],
                            string="Type")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope',
                                    domain="[('project_id','=', parent.project_id)]")
    section_name = fields.Many2one('section.line', string='Section',
                                   domain="[('project_scope','=', project_scope), ('project_id','=', parent.project_id)]")
    overhead_category = fields.Selection([
        ('product', 'Product'),
        ('petty cash', 'Petty Cash'),
        ('fuel', 'Fuel'),
        ('cash advance', 'Cash Advance')],
        string="Type")
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    product_id = fields.Many2one('product.product', string='Product')
    variable = fields.Many2one('variable.template', string='Subcon')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    cur_qty = fields.Float('Current quantity', default=0.00)
    cur_time = fields.Float('Current Time', default=0.00)
    cur_contractors = fields.Float('Current Contractors', default=0.00)
    adj_time = fields.Float('Adjusted Time', default=0.00)
    adj_contractors = fields.Float('Adjusted Contractors', default=0.00)
    adj_qty = fields.Float('Ajusted quantity', default=0.00)
    cur_unit_price = fields.Float('Current unit price', default=0.00)
    adj_unit_price = fields.Float('Ajusted unit price', default=0.00)
    cur_amt = fields.Float('Current amount', default=0.00)
    adj_amt = fields.Float('Adjusted amount', default=0.00)
    adjusted = fields.Float('Adjusted', default=0.00)

    @api.depends('job_sheet_id.change_allocation_line_cost_ids',
                 'job_sheet_id.change_allocation_line_cost_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.change_allocation_line_cost_ids:
                no += 1
                l.sr_no = no


class ChangeAllocationLineHistoryCost(models.Model):
    _name = 'change.allocation.line.history.cost'
    _description = "Change Allocation History"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
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

    @api.depends('job_sheet_id.change_allocation_line_history_cost_ids',
                 'job_sheet_id.change_allocation_line_history_cost_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.change_allocation_line_history_cost_ids:
                no += 1
                l.sr_no = no


class BudgetClaimHistoryCost(models.Model):
    _name = 'budget.claim.history.cost'
    _description = "Budget Left Claimed History"
    _order = 'sequence,id'

    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    type = fields.Selection([('material', 'Material'),
                             ('labour', 'Labour'),
                             ('overhead', 'Overhead'),
                             ('equipment', 'Equipment'),
                             ('subcon', 'Subcon')],
                            string="Type")
    project_scope_id = fields.Many2one('project.scope.line', string='Project Scope',
                                       domain="[('project_id','=', parent.project_id)]")
    section_id = fields.Many2one('section.line', string='Section',
                                 domain="[('project_scope','=', project_scope_id), ('project_id','=', parent.project_id)]")
    variable_id = fields.Many2one('variable.template', string='Variable')
    group_of_product_id = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    subcon_id = fields.Many2one('variable.template', string='Subcon')
    # description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    budget_amount = fields.Float('Budgeted Amount', default=0.00)
    budget_claim_amount = fields.Float('Budget Left Claimed Amount', default=0.00)

    @api.depends('job_sheet_id')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            if line.type == 'material':
                for l in line.job_sheet_id.material_budget_claim_history_cost_ids:
                    no += 1
                    l.sr_no = no
            elif line.type == 'labour':
                for l in line.job_sheet_id.labour_budget_claim_history_cost_ids:
                    no += 1
                    l.sr_no = no
            elif line.type == 'overhead':
                for l in line.job_sheet_id.overhead_budget_claim_history_cost_ids:
                    no += 1
                    l.sr_no = no
            elif line.type == 'equipment':
                for l in line.job_sheet_id.equipment_budget_claim_history_cost_ids:
                    no += 1
                    l.sr_no = no
            elif line.type == 'subcon':
                for l in line.job_sheet_id.subcon_budget_claim_history_cost_ids:
                    no += 1
                    l.sr_no = no


class ProjectScopeCost(models.Model):
    _name = 'project.scope.cost'
    _description = "Project Scope Cost Sheet"
    _order = 'sequence,id'

    sequence = fields.Integer(string="Sequence", default=0)
    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
    no = fields.Integer(string="No", compute="_sequence_ref")
    project_scope_id = fields.Many2one('project.scope.line', string='Project Scope')
    subtotal = fields.Float(string="Budgeted Amount")
    amount_contract = fields.Float(string="Contract Amount")
    budget_amt_left = fields.Float(string="Budgeted Amount Left")
    reserved_amt = fields.Float(string="Reserved Budget Amount")
    billed_amt = fields.Float(string="Billed Amount")
    paid_amt = fields.Float(string="Paid Amount")
    transferred_amt = fields.Float(string="Transferred Amount")
    unused_amount = fields.Float(string="Unused Amount")
    actual_used_amt = fields.Float(string="Actual Used Amount")
    allocated_budget_amt = fields.Float(string="Allocated Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Amount")
    material_line_ids = fields.One2many('material.material', 'project_scope_id', string='Material')
    labour_line_ids = fields.One2many('material.labour', 'project_scope_id', string='Labour')
    overhead_line_ids = fields.One2many('material.overhead', 'project_scope_id', string='Overhead')
    asset_line_ids = fields.One2many('internal.asset', 'project_scope_id', string='Internal Asset')
    equipment_line_ids = fields.One2many('material.equipment', 'project_scope_id', string='Equipment')
    subcon_line_ids = fields.One2many('material.subcon', 'project_scope_id', string='Subcon')

    @api.depends('job_sheet_id')
    def _sequence_ref(self):
        for rec in self:
            no = 0
            rec.no = no
            for l in rec.job_sheet_id.project_scope_cost_ids:
                no += 1
                l.no = no


class SectionCost(models.Model):
    _name = 'section.cost'
    _description = "Section Cost Sheet"
    _order = 'sequence,id'

    sequence = fields.Integer(string="Sequence", default=0)
    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet", ondelete='cascade')
    no = fields.Integer(string="No", compute="_sequence_ref")
    project_scope_id = fields.Many2one('project.scope.line', string='Project Scope')
    section_id = fields.Many2one('section.line', string='Section')
    subtotal = fields.Float(string="Budgeted Amount")
    amount_contract = fields.Float(string="Contract Amount")
    budget_amt_left = fields.Float(string="Budgeted Amount Left")
    reserved_amt = fields.Float(string="Reserved Budget Amount")
    billed_amt = fields.Float(string="Billed Amount")
    paid_amt = fields.Float(string="Paid Amount")
    transferred_amt = fields.Float(string="Transferred Amount")
    unused_amount = fields.Float(string="Unused Amount")
    actual_used_amt = fields.Float(string="Actual Used Amount")
    allocated_budget_amt = fields.Float(string="Allocated Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Amount")
    material_line_ids = fields.One2many('material.material', 'section_id', string='Material')
    labour_line_ids = fields.One2many('material.labour', 'section_id', string='Labour')
    overhead_line_ids = fields.One2many('material.overhead', 'section_id', string='Overhead')
    asset_line_ids = fields.One2many('internal.asset', 'section_id', string='Internal Asset')
    equipment_line_ids = fields.One2many('material.equipment', 'section_id', string='Equipment')
    subcon_line_ids = fields.One2many('material.subcon', 'section_id', string='Subcon')

    @api.depends('job_sheet_id')
    def _sequence_ref(self):
        for rec in self:
            no = 0
            rec.no = no
            for l in rec.job_sheet_id.section_cost_ids:
                no += 1
                l.no = no


class InterwarehouseTransferHistory(models.Model):
    _name = 'interwarehouse.transfer.history'
    _description = "Inter-warehouse Transfer History"

    no = fields.Integer(string="No", compute="_sequence_ref")
    name = fields.Char(string="Description")
    document_id = fields.Many2one('stock.picking', string="Document")
    date = fields.Date(string="Date")
    job_cost_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet")
    source_location_id = fields.Many2one('stock.location', string="From")
    destination_location_id = fields.Many2one('stock.location', string="To")
    group_of_product_id = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string="Description")
    transferred_qty = fields.Float(string="Transferred Quantity")

    @api.depends('job_cost_sheet_id')
    def _sequence_ref(self):
        for rec in self:
            no = 0
            rec.no = no
            for l in rec.job_cost_sheet_id.interwarehouse_transfer_history_ids:
                no += 1
                l.no = no
