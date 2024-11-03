# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, _logger
from lxml import etree


class ProjectProject(models.Model):
    _inherit = 'project.project'

    _sql_constraints = [("project_short_name", "unique (project_short_name)",
                         "The short name already used. please change the short name !")]
                         
    @api.constrains('name')
    def _check_existing_record(self):
        for record in self:
            name_id = self.env['project.project'].search(
                [('name', '=', record.name),
                ('company_id', '=', self.env.company.id)])
            if len(name_id) > 1:
                raise ValidationError(
                    f'The Project name already exists. Please change the Project name.')
    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]
    
    @api.model
    def _domain_warehouse(self):
        return [('company_id','=', self.env.company.id)]

    
    project_id = fields.Char(string="Project ID", readonly=True, required=True, copy=False, default='New')
    project_short_name = fields.Char(string="Short Name", size=5, track_visibility='onchange')
    created_date = fields.Date("Creation Date", default=fields.Date.today, readonly=True)
    created_by = fields.Many2one("res.users", string="Created By", default=lambda self: self.env.uid, readonly=True)
    start_date = fields.Date(string='Planned Start Date')
    end_date = fields.Date(string='Planned End Date')
    act_start_date = fields.Date(string='Actual Start Date')
    act_end_date = fields.Date(string='Actual End Date')
    payment_states = fields.Selection([
        ('settled', 'Settled'),
        ('ongoing', 'Ongoing'),
        ('late', 'Late'),
    ], string='Payment States')
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=_domain_branch)
    department_type = fields.Selection([
        ('department', 'Internal'),
        ('project', 'External'),
    ], string='Type of Project')
    # project_scope_line_ids = fields.One2many('project.scope.line', 'scope_id')
    # section_ids = fields.One2many('section.line', 'section_id')
    # TODO : need to remove
    project_scope_ids = fields.One2many('project.scope.project', 'scope_id')
    project_section_ids = fields.One2many('section.project', 'section_id')

    project_asset_ids = fields.One2many('project.asset', 'project_id', compute='_compute_asset')
    project_vehicle_ids = fields.One2many('project.vehicle', 'project_id', compute='_compute_vehicle')
    customer_ref = fields.Char(string="Customer Reference")
    stage_ids = fields.One2many('project.stage', 'stage_id')
    project_completion_ids = fields.One2many('project.completion.const', 'completion_id')
    project_completion = fields.Float(string='Project Completion')
    full_stage_weightage = fields.Float(string="Stage Full", compute="_compute_full_stage")

    # Total All Contract
    contract_amount = fields.Float(string='Contract Amount', compute="_compute_contract_amount")
    dp_amount = fields.Float(string="Down Payment", compute="_compute_dp_amount")
    retention1_amount = fields.Float(string="Retention 1", compute="_compute_retention1_amount")
    retention2_amount = fields.Float(string="Retention 2", compute="_compute_retention2_amount")
     
    # main contract
    main_contract_amount = fields.Float(string='Contract Amount')
    main_dp_method = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Down Payment Method", default='per')
    main_down_payment = fields.Float('Down Payment')
    main_dp_amount = fields.Float(string="Down Payment Amount", compute="_compute_main_downpayment")
    main_retention1 = fields.Float('Retention 1 (%)')
    main_retention1_amount = fields.Float(string="Retention 1 Amount", compute="_compute_main_retention1")
    main_retention1_date = fields.Date('Retention 1 Date')
    main_retention_term_1 = fields.Many2one(
        'retention.term', string='Retention 1 Term', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    main_retention2 = fields.Float('Retention 2 (%)')
    main_retention2_amount = fields.Float(string="Retention 2 Amount", compute="_compute_main_retention2")
    main_retention2_date = fields.Date('Retention 2 Date')
    main_retention_term_2 = fields.Many2one(
        'retention.term', string='Retention 2 Term', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    main_tax_id = fields.Many2many('account.tax', string='Taxes', domain=[('active', '=', True), ('type_tax_use', '=', 'sale'), ('tax_scope', '!=', False)])
    main_payment_term = fields.Many2one('account.payment.term', 'Payment Term')
    

    # Project Progress
    outstanding_limit = fields.Float(string='Outstanding Limit')
    status_progress = fields.Float(string='Status Progress')

    # Adds New Fields on Master Data Table (Construction Management > Projects > Projects )
    # Role in Project
    project_director = fields.Many2one('res.users', string='Project Manager', tracking=True)
    site_engineer = fields.Many2many('res.users', 'site_engineer_employee', string='Site Engineer')
    site_worker = fields.Many2many('res.users', 'site_worker_employee', string='Site Worker')
    sales_person_id = fields.Many2many('res.users', 'sales_person_employee', string='Sales Person')
    estimator = fields.Many2many('res.users', 'estimator_employee', string='Estimator')
    accounting_staff = fields.Many2many('res.users', 'accounting_staff_employee', string='Accounting Staff')
    sales_staff = fields.Many2many('res.users', 'sales_staff_employee', string='Sales Staff')
    
    project_coordinator = fields.Many2one('res.users', string='Project Coordinator')
    project_team_ids = fields.Many2many(relation='project_associated_rel', comodel_name='res.users',
                                        column1='project_id', column2='associated_id', default=lambda self: self.env.user)
    project_team_user = fields.Many2one('res.users', string='Project Team User')
    sales_team = fields.Many2one('crm.team', string='Sales Team')
    
    associated_user_ids = fields.Many2many(relation='project_associated_rel', comodel_name='res.users',
                                           column1='project_id', column2='associated_id', default=lambda self: self.env.user)
    
    # adding field to the project.project for showing the current user assigned projects
    analytic_idz = fields.Many2many('account.analytic.tag', string='Analytic Group', domain="[('company_id', '=', company_id)]", ondelete='cascade')
    show_own_records = fields.Char(string="Own Record", compute='_get_own_project_offer',
                                   search='_search_own_project_offer')
    total_job_estimate = fields.Integer(string="BOQ",compute='_comute_job_estimate')
    company_id = fields.Many2one('res.company', 'Company', readonly=True, index=True,
                                 default=lambda self: self.env.company)
    duration = fields.Text(string='Duration', compute='_compute_duration')

   # penalty
    diff_penalty = fields.Boolean(string='Different Penalty')
    method = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                              default='percentage')
    amount = fields.Float(string='Amount')
    method_client = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                              default='percentage')
    amount_client = fields.Float(string='Amount')
    responsible = fields.Selection([('contractor', 'Contractor'), ('client', 'Client')], string='Responsible of Cancellation')
    reason = fields.Text(string='Reason of Cancellation')
    
    # Location
    address = fields.Text(tracking=True)
    street = fields.Char('Street', tracking=True)
    street_2 = fields.Char('Street2', tracking=True)
    city = fields.Char('City', tracking=True)
    state_id = fields.Many2one('res.country.state',string="State", tracking=True)
    country_id = fields.Many2one('res.country',string="Country", tracking=True)
    zip_code = fields.Char('Zip', tracking=True)

    # Warehouse
    warehouse_address = fields.Many2one('stock.warehouse', string='Warehouse',domain=_domain_warehouse)
    warehouse_location_ids = fields.One2many('stock.location', 'project', string="Warehouse Internal Location")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", check_company=True, ondelete='cascade',
        help="Analytic account to which this project is linked for financial management. "
             "Use an analytic account to record cost and revenue on your project.")
    #unused
    warehouse_location = fields.Many2many(relation='project_location_rel', comodel_name='stock.location',
                                        column1='associated_id', column2='project_id',string="Warehouse Internal Location (invisible)")
    warehouse_location_table_ids = fields.One2many('warehouse.location.table', 'project_id', string="Warehouse Internal Location (invisible)")

    # Add different states in project model for business needs
    primary_states = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'In Progress'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('lost', 'Lost'),
    ], string='Primary States', default='draft')
    project_scope_computed = fields.Many2many('project.scope.line', string='Project Scope', compute="get_scope_ids")
    
    addendum_line_ids = fields.One2many('addendum.line', 'addendum_id')
    variation_order_ids = fields.One2many('variation.order.line', 'project_id')
    variation_order_internal_ids = fields.One2many('variation.order.internal.line', 'project_id')
    guarantee_table_ids = fields.One2many('guarantee.table', 'project_id')
    is_using_labour_attendance = fields.Boolean(string='Labour Cost Attendance')
    project_location_ids = fields.One2many('project.location', 'project_id', string="Project Locations")
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ProjectProject, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if not self.env.context.get('is_sale_project'):
            if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer'):
                root = etree.fromstring(res['arch'])
                root.set('create', 'false')
                root.set('edit', 'false')
                root.set('delete', 'false')
                res['arch'] = etree.tostring(root)
            elif self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group('abs_construction_management.group_construction_manager'):
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
                
            if self.env.context.get('is_project_job_order'):
                root.set('create', 'false')
                res['arch'] = etree.tostring(root)
            
        return res
    
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                difference_days = (record.end_date - record.start_date).days
                record.duration = f'{str(difference_days)} days'
            else:
                record.duration = False

            
    def custom_menu(self):
        views = [(self.env.ref('equip3_construction_masterdata.view_project_kanban_const').id,'kanban'),
                  (self.env.ref('project.view_project').id,'tree'),
                 (self.env.ref('project.edit_project').id,'form'),
                 ]
        # query_paramaters = []
        # query_statement = """
        #     SELECT id FROM job_cost_sheet 
        #     """
        if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
              return {
                'type': 'ir.actions.act_window',
                'name': 'Projects',
                'res_model': 'project.project',
                'view_mode': 'kanban,tree,form',
                'views':views,
                'domain': [('department_type', '=', 'department'),('id','in',self.env.user.project_ids.ids)],
                'context':{'default_department_type': 'department'},
                'help':"""
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
                'views':views,
                'domain': [('department_type', '=', 'department')],
                'context':{'default_department_type': 'department'},
                'help':"""
                 <p class="oe_view_nocontent_create">
                    Create a new project.
                </p><p>
                    Organize your activities (plan tasks, track issues, invoice timesheets) for internal, personal or customer projects.
                </p>
            """
            }

    @api.depends('main_dp_method','main_down_payment', 'main_contract_amount')
    def _compute_main_downpayment(self):
        for res in self:
            if res.main_dp_method == 'per':
                res.main_dp_amount = res.main_contract_amount * (res.main_down_payment / 100)
            elif res.main_dp_method == 'fix':
                res.main_dp_amount = res.main_down_payment
            else:
                res.main_dp_amount = 0

    @api.depends('main_retention1', 'main_contract_amount')
    def _compute_main_retention1(self):
        for res in self:
            res.main_retention1_amount = res.main_contract_amount * (res.main_retention1 / 100)

    @api.depends('main_retention2', 'main_contract_amount')
    def _compute_main_retention2(self):
        for res in self:
            res.main_retention2_amount = res.main_contract_amount * (res.main_retention2 / 100)
    
    @api.depends('variation_order_ids.contract_amount','main_contract_amount')
    def _compute_contract_amount(self):
        total1 = 0
        for res1 in self:
            total1 = sum(res1.variation_order_ids.mapped('contract_amount'))
            res1.contract_amount = total1 + res1.main_contract_amount
        return total1

    @api.depends('variation_order_ids.dp_amount','main_dp_amount')
    def _compute_dp_amount(self):
        total2 = 0
        for res2 in self:
            total2 = sum(res2.variation_order_ids.mapped('dp_amount'))
            res2.dp_amount = total2 + res2.main_dp_amount
        return total2

    @api.depends('variation_order_ids.retention1_amount','main_retention1_amount')
    def _compute_retention1_amount(self):
        total3 = 0
        for res3 in self:
            total3 = sum(res3.variation_order_ids.mapped('retention1_amount'))
            res3.retention1_amount = total3 + res3.main_retention1_amount
        return total3

    @api.depends('variation_order_ids.retention2_amount', 'main_retention2_amount')
    def _compute_retention2_amount(self):
        total4 = 0
        for res4 in self:
            total4 = sum(res4.variation_order_ids.mapped('retention2_amount'))
            res4.retention2_amount = total4 + res4.main_retention2_amount
        return total4
    
    def _get_own_project_offer(self):
        _logger.info("user can show only his projects")

    def _search_own_project_offer(self, operator, value):
        user_pool = self.env['res.users']
        user = user_pool.browse(self._uid)
        project_ids = user.project_ids
        if project_ids:
            return [('id', 'in', project_ids.ids)]
        else:
            return [('id', '=', -1)]
    

    def _comute_job_estimate(self):
        for job in self:
            job_count = self.env['job.estimate'].search_count([('project_id', '=', self.id), ('state', '=', 'sale')])
            job.total_job_estimate = job_count

    def action_job_estimate(self):
        return {
            'name': ("BOQ"),
            'view_mode': 'tree,form',
            'res_model': 'job.estimate',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_id', '=', self.id), ('state', '=', 'sale')],
        }
    
    def project_scope_count(self):
        count = 0
        for rec in self:
            for count in rec.project_scope_line_ids:
                count += 1
        return count

    def section_count(self):
        count = 0
        for rec in self:
            for count in rec.section_ids:
                count += 1
        return count

    def button_verify(self):
        """
        Set state to verified for current project
        """
        for rec in self:
            if rec.cost_sheet_count == 0:
                raise ValidationError("cost sheet is not created")
            elif rec.section_count == 0 or rec.project_scope_count == 0:
                raise ValidationError("Project Scope/Section cannot be empty")
            else:
                rec.primary_states = 'progress'

    def button_suspend(self):
        """
        Set state to suspended  for current project
        """
        for rec in self:
            rec.primary_states = 'suspended'

    def button_complete(self):
        project_issue = self.env['project.issue'].search([('project_id', '=', self.id), ('state', 'in', ('found', 'in_progress'))])
        project_task = self.env['project.task'].search([('project_id', '=', self.id), ('state', 'in', ('draft', 'inprogress', 'pending'))])
        if project_issue:
             raise ValidationError(_("Please solve or cancel the issues to complete this project"))
        elif project_task:
           raise ValidationError(_("Please complete or cancel the job order to complete this project"))
        else:
            self.primary_states = 'completed'

    def button_continue(self):
        """
        Set state to continue for current project
        """
        for rec in self:
            rec.primary_states = 'progress'

    def button_cancel(self):
        """
        Set state to cancel for current project
        """
        # for rec in self:
        #     rec.primary_states = 'cancelled'
        return {
            'name': _('Project Cancellation'),
            'res_model': 'project.cancel.responsible',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {
                'default_project_id': self.id,
            }
        }

    def button_rest_draft(self):
        """
        Set state to draft for current project
        """
        for rec in self:
            rec.primary_states = 'draft'
    
    @api.model
    def create(self, vals):
        # Prevent double project creation
        self = self.with_context(mail_create_nosubscribe=True)
        vals['project_id'] = self.env['ir.sequence'].next_by_code(
            'project.seq') or 'New'
        project = super(ProjectProject, self).create(vals)

        if not vals.get('subtask_project_id'):
            project.subtask_project_id = project.id
        if project.privacy_visibility == 'portal' and project.partner_id.user_ids:
            project.allowed_user_ids |= project.partner_id.user_ids
        return project
    
    def _inprogress_project_warehouse(self):
        warehouse = False
        values={}
        values['company_id'] = self.env.company.id
        values['name'] = self.name
        values['code'] = self.project_short_name
        values['branch_id'] = self.branch_id.id
        if self.project_short_name:
            exist_warehouse = self.env['stock.warehouse'].search([('code','=', self.project_short_name)])
            if exist_warehouse:
                for warehouse_ids in exist_warehouse:
                    location_val = self.env['stock.location'].search([('location_id.name','=', self.project_short_name)])
                    warehouse_ids.project = self.id
                    for location_ids in location_val:
                        location_ids.project = self.id
            else:
                warehouse = self._create_warehouse(values)
                self.write({'warehouse_address': warehouse.id})
                if warehouse:
                    for warehouse_ids in warehouse:
                        location_val = self.env['stock.location'].search([('location_id.name','=', self.project_short_name)])
                        warehouse_ids.project = self.id
                        for location_ids in location_val:
                            location_ids.project = self.id

    @api.model
    def _create_warehouse(self, values):
        warehouse = self.env['stock.warehouse'].create(values)
        return warehouse

    @api.onchange('warehouse_address')
    def onchange_warehouse_location_table_ids(self):
        vals={}
        new=[]
        for res in self:
            warehouse = self.env['stock.location'].search([('warehouse_id','=',res.warehouse_address.id)])
            for location in warehouse:
                if location.name != res.warehouse_address.code:
                    new.append(location.id)
                    vals['location_id'] = location.id
            for res_location in res.warehouse_location_table_ids:
                for change in new:
                    res_location.internal_location = change
                    new.pop(0)
                    break
            break

    @api.depends('stage_ids.stage_weightage')
    def _compute_full_stage(self):
        for res in self:
            res.full_stage_weightage = sum(res.stage_ids.mapped('stage_weightage'))

    @api.onchange('full_stage_weightage')
    def onchange_stage_weightage(self):
        if self.full_stage_weightage > 100:
            raise ValidationError(_("The total of stage weightage is more than 100%.\nPlease, re-set the weightage of each stage."))

    @api.onchange('project_scope_ids')
    def _check_exist_project_scope_form(self):
        for scope in self:
            exist_scope_list = []
            for line in scope.project_scope_ids:
                if line.project_scope.id in exist_scope_list:
                    raise ValidationError(_('The Project Scope "%s" already exists. Please change this Project Scope (must be unique).'%((line.project_scope.name))))
                exist_scope_list.append(line.project_scope.id)

    @api.onchange('project_section_ids')
    def _check_exist_section_form(self):
        for section in self:
            exist_section_list = []
            for line in section.project_section_ids:
                same = str(line.project_scope.id) + ' - ' + str(line.section.id)
                if same in exist_section_list:
                    raise ValidationError(_('The Section "%s" already exists  in project scope "%s". Please change this Section.'%((line.section.name),(line.project_scope.name))))
                exist_section_list.append(same)

    # compute auto fill asset
    def _compute_asset(self):
        for rec in self:
            asset_vals = []
            project_asset = self.env['project.asset']
            maintenance_equipment = self.env['maintenance.equipment'].search([('project_id', '=', rec.id)])
            for asset in maintenance_equipment:
                if asset.vehicle_checkbox == False:
                    asset_val = {
                        "project_id" : asset.project_id.id,
                        "equipment_name" : asset.id,
                        "asset_category_id" : asset.category_id.id,
                        "facilities_area_id" : asset.fac_area.id,
                        "serial_no" : asset.serial_no,
                    }
                    asset_vals.append(asset_val)
            for fill in asset_vals:
                rec.project_asset_ids = [(0, 0, fill)]
            # prevent error if no record found 
            if asset_vals == []:
                rec.project_asset_ids = [(0, 0, {})]
            # end prevent error if no record found 
            super(ProjectAsset, project_asset).create(asset_vals)
    # end compute auto fill asset

    # compute auto fill vehicle
    def _compute_vehicle(self):
        for rec in self:
            vehicle_vals = []
            project_vehicle = self.env['project.vehicle']
            maintenance_equipment = self.env['maintenance.equipment'].search([('project_id', '=', rec.id)])
            for vehicle in maintenance_equipment:
                if vehicle.vehicle_checkbox == True:
                    vehicle_val = {
                        "project_id" : vehicle.project_id.id,
                        "equipment_name" : vehicle.id,
                        "asset_category_id" : vehicle.category_id.id,
                        "facilities_area_id" : vehicle.fac_area.id,
                        "serial_no" : vehicle.serial_no,
                    }
                    vehicle_vals.append(vehicle_val)
            for fill in vehicle_vals:
                rec.project_vehicle_ids = [(0, 0, fill)]
            # prevent error if no record found 
            if vehicle_vals == []:
                rec.project_vehicle_ids = [(0, 0, {})]
            # end prevent error if no record found 
            super(ProjectVehicle, project_vehicle).create(vehicle_vals)
    # end compute auto fill vehicle

    
    @api.depends('project_scope_ids.project_scope')
    def get_scope_ids(self):
        for rec in self:
            scope_ids = []
            for line in rec.project_scope_ids:
                if line.project_scope:
                    scope_ids.append(line.project_scope.id)
            rec.project_scope_computed = [(6, 0, scope_ids)]


class ProjectLocation(models.Model):
    _name = "project.location"
    _description = "Project Location"

    name = fields.Char(string="Name", compute="_compute_name")
    project_id = fields.Many2one('project.project', string="Project")
    active_location_id = fields.Many2one('res.partner', string="Active Location", domain=[('is_project_location', '=', True)], required=True)
    # Location
    address = fields.Text()
    street = fields.Char('Street', related='active_location_id.street')
    street_2 = fields.Char('Street2', related='active_location_id.street2')
    city = fields.Char('City', related='active_location_id.city')
    state_id = fields.Many2one('res.country.state',string="State", related='active_location_id.state_id')
    country_id = fields.Many2one('res.country',string="Country", related='active_location_id.country_id')
    zip_code = fields.Char('Zip', related='active_location_id.zip')

    date_localization = fields.Date(string='Geolocation Date', related='active_location_id.date_localization')
    latitude = fields.Float(string='Latitude', related='active_location_id.partner_latitude')
    longitude = fields.Float(string='Longitude', related='active_location_id.partner_longitude')
    attendance_range = fields.Integer(string='Attendance Range', related='active_location_id.attendance_range')

    @api.depends('active_location_id')
    def _compute_name(self):
        for record in self:
            record.name = record.active_location_id.name

    @api.model
    def _geo_localize(self, street='', zip='', city='', state='', country=''):
        geo_obj = self.env['base.geocoder']
        search = geo_obj.geo_query_address(street=street, zip=zip, city=city, state=state, country=country)
        result = geo_obj.geo_find(search, force_country=country)
        if result is None:
            search = geo_obj.geo_query_address(city=city, state=state, country=country)
            result = geo_obj.geo_find(search, force_country=country)
        return result

    def geo_localize(self):
        # We need country names in English below
        for record in self.with_context(lang='en_US'):
            result = self._geo_localize(record.street,
                                        record.zip_code,
                                        record.city,
                                        record.state_id.name,
                                        record.country_id.name)

            if result:
                record.write({
                    'latitude': result[0],
                    'longitude': result[1],
                    'date_localization': fields.Date.context_today(record)
                })
        return True


class ProjectScopeProject(models.Model):
    _name = "project.scope.project"
    _description = "Project Scope"
    _order = "sequence" 

    scope_id = fields.Many2one('project.project', string="Project")
    sequence = fields.Integer(string="Sequence", default=1)
    sr_no = fields.Integer(string="No.", compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    description = fields.Text(string='Description')

    @api.depends('scope_id.project_scope_ids', 'scope_id.project_scope_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.scope_id.project_scope_ids:
                no += 1
                l.sr_no = no

class SectionLineProject(models.Model):
    _name = "section.project"
    _description = "Section"
    _order = "sequence"

    section_id = fields.Many2one('project.project', string="Project")
    sequence = fields.Integer(string="Sequence", default=1)
    sr_no = fields.Integer(string="No.", compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    description = fields.Text(string='Description')
    quantity = fields.Float('Quantity', default=1)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    
    @api.depends('section_id.project_section_ids', 'section_id.project_section_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.section_id.project_section_ids:
                no += 1
                l.sr_no = no


    @api.onchange('section')
    def onchange_section(self):
        for res in self:
            unit = self.env['uom.uom'].search([('name', '=', 'Units')],limit=1)
            if res.section:
                if unit:
                    res.write({'uom_id': unit.id})


class ProjectStage(models.Model):
    _name = "project.stage"
    _description = "Stage"
    _order = "sequence"

    @api.depends('stage_id.stage_ids', 'stage_id.stage_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.stage_id.stage_ids:
                no += 1
                l.sr_no = no

    stage_id = fields.Many2one('project.project', string="Project")
    sequence = fields.Integer(string="Sequence", default=1)
    sr_no = fields.Integer(string="Sequence", compute="_sequence_ref")
    name = fields.Many2one('project.task.type', string="Stage")
    stage_weightage = fields.Float(string="Stage Weightage (%)")
    project_id = fields.Char(related='stage_id.name', string='Project')


class ProjectTaskTypeInherit(models.Model):
    _inherit = 'project.task.type'

    company_id = fields.Many2one('res.company', 'Company', index=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    department_type = fields.Selection(related='project_ids.department_type', string='Type of Department')
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ProjectTaskTypeInherit, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        root = etree.fromstring(res['arch'])
        if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer'):
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        return res
    
    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if rec.department_type == 'project':
                return {
                    'domain': {'project_ids': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id)]}
                }
            elif rec.department_type == 'department':
                return {
                    'domain': {'project_ids': [('department_type', '=', 'department'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id)]}
                }


class ProjectCompletion(models.Model):
    _name = "project.completion.const"
    _description = "Project Completion"
    _order = "sequence"

    @api.depends('completion_id.project_completion_ids', 'completion_id.project_completion_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.completion_id.project_completion_ids:
                no += 1
                l.sr_no = no

    @api.onchange('stage_details_ids')
    def onchange_stage_weightage(self):
        for res in self:
            stage_full = sum(res.stage_details_ids.mapped('stage_weightage'))
            if stage_full > 100:
                raise ValidationError(_("The total of stage weightage is more than 100%.\nPlease, re-set the weightage of each stage."))
             
    completion_id = fields.Many2one('project.project', string="Project")
    sequence = fields.Integer(string="Sequence", default=1)
    sr_no = fields.Integer(string="Sequence", compute="_sequence_ref")
    contract_percentage = fields.Float(string="Contract Percentage of The Project")
    project_completion = fields.Float(string="Contract Completion")
    stage_details_ids = fields.One2many('project.stage.const', 'stage_id')
    project_id = fields.Char(related='completion_id.name', string='Project')


class ProjectStageNew(models.Model):
    _name = "project.stage.const"
    _description = "Stage Details"
    _order = "sequence"

    @api.depends('stage_id.stage_details_ids', 'stage_id.stage_details_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.stage_id.stage_details_ids:
                no += 1
                l.sr_no = no

    stage_id = fields.Many2one('project.completion.const', string="Contract")
    sequence = fields.Integer(string="Sequence", default=1)
    sr_no = fields.Integer(string="Sequence", compute="_sequence_ref")
    name = fields.Many2one('project.task.type', string="Stage")
    stage_weightage = fields.Float(string="Stage Weightage (%)")
    stage_completion = fields.Float(string="Stage Completion")
    project_id = fields.Char(related='stage_id.project_id', string='Project')


class ProjectAsset(models.Model):
    _name = 'project.asset'
    _description = "Asset"
    _order = 'sequence'

    project_id = fields.Many2one('project.project', string='Project')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    equipment_name = fields.Many2one('maintenance.equipment', string='Equipment Name')
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category')
    facilities_area_id = fields.Many2one('maintenance.facilities.area', string='Facilities Area')
    serial_no = fields.Char('Serial Number')

    @api.depends('project_id.project_asset_ids', 'project_id.project_asset_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_id.project_asset_ids:
                no += 1
                l.sr_no = no

    @api.onchange('equipment_name')
    def onchange_equipment(self):
        if self.equipment_name and self.equipment_name.vehicle_checkbox != True:
            if self.equipment_name.category_id:
                self.asset_category_id = self.equipment_name.category_id.id
            if self.equipment_name.fac_area:
                self.facilities_area_id = self.equipment_name.fac_area.id
            if self.equipment_name.serial_no:
                self.serial_no = self.equipment_name.serial_no

class ProjectVehicle(models.Model):
    _name = 'project.vehicle'
    _description = "Vehicle"
    _order = 'sequence'

    project_id = fields.Many2one('project.project', string='Project')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    equipment_name = fields.Many2one('maintenance.equipment', string='Equipment Name')
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category')
    facilities_area_id = fields.Many2one('maintenance.facilities.area', string='Facilities Area')
    serial_no = fields.Char('Serial Number')

    @api.depends('project_id.project_vehicle_ids', 'project_id.project_vehicle_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_id.project_vehicle_ids:
                no += 1
                l.sr_no = no

    @api.onchange('equipment_name')
    def onchange_equipment(self):
        if self.equipment_name and self.equipment_name.vehicle_checkbox == True:
            if self.equipment_name.category_id:
                self.asset_category_id = self.equipment_name.category_id.id
            if self.equipment_name.fac_area:
                self.facilities_area_id = self.equipment_name.fac_area.id
            if self.equipment_name.serial_no:
                self.serial_no = self.equipment_name.serial_no
