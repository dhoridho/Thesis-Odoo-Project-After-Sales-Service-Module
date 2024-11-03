from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.http import request
from datetime import datetime, date, timedelta
import pytz
from lxml import etree
import json

class PlanTaskCheckList(models.Model):
    _name = 'plan.task.check.list'
    _description = 'Plan Task Check List'
    _inherit = 'vehicle.parts'

    equipment_id = fields.Many2one('maintenance.equipment', string='Asset Type')
    vehicle_parts_ids = fields.Many2many('vehicle.parts', string='Parts')
    task = fields.Text('Task')
    maintenance_plan_id = fields.Many2one('maintenance.plan')
    maintenance_wo_id = fields.Many2one('maintenance.work.order')
    maintenance_ro_id = fields.Many2one('maintenance.repair.order')
    is_odometer_m_plan = fields.Boolean(string='Odometer Plan')
    already_compute = fields.Boolean(string='Already Compute')

    asset_description = fields.Char()
    is_checklist = fields.Boolean()

    @api.model
    def default_get(self, fields_list):
        defaults = super(PlanTaskCheckList, self).default_get(fields_list)
        if self._context.get('is_odometer_m_plan'):
            defaults['is_odometer_m_plan'] = True
            if self._context.get('params'):
                defaults['maintenance_plan_id'] = self._context.get('params').get('id')
        return defaults

    @api.onchange('equipment_id')
    def onchange_equipment_id(self):
        if self.maintenance_ro_id.state_id == 'draft' or self.maintenance_wo_id.state_id == 'draft':
            self.vehicle_parts_ids = [(6, 0, self.equipment_id.vehicle_parts_ids.ids)]

        if self.maintenance_plan_id.state == 'draft':
            self.vehicle_parts_ids = [(6, 0, self.equipment_id.vehicle_parts_ids.ids)]
            

    def _get_asset_budget(self, asset):
        AssetBudget = self.env['asset.budget.accounting']
        
        if self.maintenance_wo_id:
            branch_ids = self.maintenance_wo_id.branch_id.ids
            analytic_group_ids = self.maintenance_wo_id.analytic_group_id.ids
            start_date = self.maintenance_wo_id.startdate
            end_date = self.maintenance_wo_id.enddate
        
        if self.maintenance_ro_id:
            branch_ids = self.maintenance_ro_id.branch_id.ids
            analytic_group_ids = self.maintenance_ro_id.analytic_group_id.ids
            start_date = self.maintenance_ro_id.date_start
            end_date = self.maintenance_ro_id.date_stop
        
        
        asset_budgets = AssetBudget.search([
            ('branch_id', 'in', branch_ids), 
            ('date_from', '<=', start_date), 
            ('date_to', '>=', end_date), 
            ('account_tag_ids', 'in', analytic_group_ids),
            ('state', '=', 'validate'),
        ])
        
        if asset_budgets:
            for asset_budget in asset_budgets:
                for line in asset_budget.asset_budget_line_ids:
                    if line.asset_budgetary_position_id.id == asset.id:
                        return line.remaining_amount
        
        return 0.0
    
        
PlanTaskCheckList()


class MaintenanceMaterialsList(models.Model):
    _name = 'maintenance.materials.list'
    _description = 'Maintenance Materials List'

    equipment_id = fields.Many2one('maintenance.equipment', string='Materials')
    notes = fields.Char('Notes')
    maintenance_plan_id = fields.Many2one('maintenance.plan')
    maintenance_wo_id = fields.Many2one('maintenance.work.order')
    maintenance_ro_id = fields.Many2one('maintenance.repair.order')
    product_id = fields.Many2one('product.product', string='Tools')
    uom_id = fields.Many2one('uom.uom', string='Tools')
    product_uom_qty = fields.Float(string='Quantity', default=1)
    analytic_group_ids = fields.Many2many('account.analytic.tag', string='Analytic Group')
    location_id = fields.Many2one('stock.location', string="Source Location")
    location_dest_id = fields.Many2one('stock.location', string="Destination Location", domain="[('usage', '=', 'internal')]")
    move_id = fields.Many2one('stock.move', string="Move")
    filter_location_ids = fields.Many2many('stock.location', string='Source Location', compute='_get_locations', store=False)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use', '=', 'sale')], default=lambda self: self.env.company.account_sale_tax_id)
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    invoiced_price = fields.Float('Invoiced Price')
    price_subtotal = fields.Monetary(compute='_compute_amount_price', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount_price', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount_price', string='Tax', store=True)
    types = fields.Selection([("add","Add"),("remove","Remove")], string='Type', default="add")
    loc_is_required = fields.Boolean(string='Location is required', compute='_compute_loc_is_required')
    part_equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Parts')
    part_equipment_id_domain = fields.Char(string='Parts Domain', compute='_compute_part_equipment_id_domain')
    parent_equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Parent Equipment', required=True)
    parent_equipment_id_domain = fields.Char(comodel_name='maintenance.equipment', string='Parent Equipment Domain', compute='_compute_parent_equipment_id_domain')
    attachment = fields.Binary(string='Attachment', attachment=True)
    file_name = fields.Char(string='File Name')    

    @api.depends('product_id', 'types', 'maintenance_wo_id', 'maintenance_ro_id')
    def _compute_loc_is_required(self):
        for record in self:
            if record.maintenance_ro_id:
                if record.types == 'add' and record.product_id.type in ['product', 'consu']:
                    record.loc_is_required = True
                else:
                    record.loc_is_required = False
            elif record.maintenance_wo_id:
                if record.product_id.type in ['product', 'consu']:
                    record.loc_is_required = True
                else:
                    record.loc_is_required = False

    @api.depends('product_uom_qty', 'price_unit', 'taxes_id')
    def _compute_amount_price(self):
        for line in self:
            vals = line._prepare_compute_all_values()
            taxes = line.taxes_id.compute_all(
                vals['price_unit'],
                vals['currency_id'],
                vals['product_uom_qty'])
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    def _prepare_compute_all_values(self):
        self.ensure_one()
        return {
            'price_unit': self.price_unit,
            'currency_id': self.maintenance_wo_id.currency_id,
            'currency_id': self.maintenance_ro_id.currency_id,
            'product_uom_qty': self.product_uom_qty,
        }

    @api.depends('product_id')
    def _get_locations(self):
        for record in self:
            data_ids = []
            location_ids = []
            if record.product_id.type == 'product':
                stock_quant = record.env['stock.quant'].search([('product_id','=', record.product_id.id)])
                for quant in stock_quant:
                    if quant.available_quantity > 0 and quant.location_id.usage == 'internal':
                        location_ids.append(quant.location_id.id)
            else:
                locations = record.env['stock.location'].search([('usage', '=', 'internal')])
                for location in locations:
                    location_ids.append(location.id)
            record.filter_location_ids = [(6, 0, location_ids)]

    @api.depends('product_uom_qty','price_unit')
    def _amount_all(self):
        for rec in self:
            rec.price_subtotal = rec.product_uom_qty * rec.price_unit
            
    def _get_product_warehouse_price(self, product_id, warehouse_id):
        is_cost_per_warehouse = self.env['ir.config_parameter'].sudo().get_param(
            'equip3_inventory_base.is_cost_per_warehouse', False)
        if is_cost_per_warehouse:
            product_price = self.env['product.warehouse.price'].sudo().search(
                [('product_id', '=', product_id), ('warehouse_id', '=', warehouse_id)], limit=1).standard_price or 0
        else:
            product_price = self.env['product.product'].browse(
                product_id).standard_price
        return product_price or self.env['product.product'].browse(product_id).standard_price
    
    @api.onchange('product_id', 'location_id')
    def onchange_product_and_location(self):
        if self._context.get('is_maintenance'):
            if self.product_id and self.location_id:
                self.price_unit = self._get_product_warehouse_price(self.product_id.id, self.location_id.warehouse_id.id)
            
    @api.onchange('product_id', 'types')
    def on_change_product(self):
        self.uom_id = self.product_id.uom_id.id
        if self._context.get('is_maintenance'):
            for material in self.maintenance_wo_id.task_check_list_ids.mapped('equipment_id').mapped('maintenance_materials_list_ids'):
                if material.product_id == self.product_id:
                    self.location_id = material.location_id
                    self.location_dest_id = material.location_dest_id
                    break
        if self._context.get('is_repair'):
            for repair in self.maintenance_ro_id.task_check_list_ids.mapped('equipment_id').mapped('maintenance_materials_list_ids'):
                if repair.product_id == self.product_id:
                    self.location_id = repair.location_id
                    self.location_dest_id = repair.location_dest_id
                    break
            # ------ set location & type -------
            # self.types = 'remove'
            if self.types == 'remove':
                location_id = self.env['stock.location'].search([('name', 'ilike', 'Scrap'), ('company_id','=', self.env.company.id)], limit=1)
                if location_id:
                    self.location_id = location_id.id

                location_dest_id = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id','=', self.env.company.id)], limit=1)
                if location_dest_id:
                    self.location_dest_id = location_dest_id.id
                if not self.location_id or not self.location_dest_id:
                    location_id = self.env['stock.location'].search([('name', 'ilike', 'Scrap'), ('company_id','=', self.env.company.id)], limit=1)
                    if location_id:
                        self.location_id = location_id.id

                    location_dest_id = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id','=', self.env.company.id)], limit=1)
                    if location_dest_id:
                        self.location_dest_id = location_dest_id.id

            if self.types == 'add':
                location_dest_id = self.env['stock.location'].search([('name', 'ilike', 'Scrap'), ('company_id','=', self.env.company.id)], limit=1)
                if location_dest_id:
                    self.location_dest_id = location_dest_id.id

                location_id = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id','=', self.env.company.id)], limit=1)
                if location_id:
                    self.location_id = location_id.id

                if not self.location_id or not self.location_dest_id:
                    location_dest_id = self.env['stock.location'].search([('name', 'ilike', 'Scrap'), ('company_id','=', self.env.company.id)], limit=1)
                    if location_dest_id:
                        self.location_dest_id = location_dest_id.id

                    location_id = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id','=', self.env.company.id)], limit=1)
                    if location_id:
                        self.location_id = location_id.id


    @api.model
    def default_get(self, fields):
        vals = super(MaintenanceMaterialsList, self).default_get(fields)
        if self._context.get('is_scrap_location'):
            location_dest_id = self.env['stock.location'].search([('name','ilike','Scrap')],limit =1)
            if location_dest_id:
                vals['location_dest_id'] = location_dest_id.id
        return vals

    @api.depends('maintenance_wo_id', 'maintenance_ro_id')
    def _compute_part_equipment_id_domain(self):
        for record in self:
            record.part_equipment_id_domain = False
            maintenance_id = record.maintenance_wo_id or record.maintenance_ro_id
            if maintenance_id:
                equipment_ids = record.parent_equipment_id.vehicle_parts_ids.mapped('equipment_id').ids
                record.part_equipment_id_domain = json.dumps([('id', 'in', equipment_ids)])

    @api.depends('maintenance_wo_id', 'maintenance_ro_id')
    def _compute_parent_equipment_id_domain(self):
        for record in self:
            record.parent_equipment_id_domain = False
            maintenance_id = record.maintenance_wo_id or record.maintenance_ro_id
            if maintenance_id:
                equipment_ids = maintenance_id.task_check_list_ids.mapped('equipment_id').ids
                record.parent_equipment_id_domain = json.dumps([('id', 'in', equipment_ids)])


MaintenanceMaterialsList()

class MaintenanceEquipmentMaterialsList(models.Model):
    _name = 'maintenance.equipment.materials.list'
    _description = 'Maintenance Equipment Materials List'

    equipment_id = fields.Many2one('maintenance.equipment', string='Materials')
    notes = fields.Char('Notes')
    product_id = fields.Many2one('product.product', string='Tools')
    uom_id = fields.Many2one('uom.uom', string='Tools')
    product_uom_qty = fields.Float(string='Quantity', default=1)
    analytic_group_ids = fields.Many2many('account.analytic.tag', string='Analytic Group')
    location_id = fields.Many2one('stock.location', string="Source Location")
    location_dest_id = fields.Many2one('stock.location', string="Destination Location", domain="[('usage', '=', 'internal')]")
    move_id = fields.Many2one('stock.move', string="Move")
    filter_location_ids = fields.Many2many('stock.location', stirng='Source Location', compute='_get_locations', store=False)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use', '=', 'sale')], default=lambda self: self.env.company.account_sale_tax_id)
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    invoiced_price = fields.Float('Invoiced Price')
    price_subtotal = fields.Monetary(compute='_compute_amount_price', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount_price', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount_price', string='Tax', store=True)
    types = fields.Selection([("add","Add"),("remove","Remove")], string='Type', default="add")
    equipment_part_id_domain = fields.Char(compute='_get_equipment_part_id_domain')
    equipment_part_id = fields.Many2one(comodel_name='maintenance.equipment', string='Part')

    @api.depends('product_uom_qty', 'price_unit', 'taxes_id')
    def _compute_amount_price(self):
        for line in self:
            vals = line._prepare_compute_all_values()
            taxes = line.taxes_id.compute_all(
                vals['price_unit'],
                vals['currency_id'],
                vals['product_uom_qty'])
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    def _prepare_compute_all_values(self):
        self.ensure_one()
        return {
            'price_unit': self.price_unit,
            'currency_id': self.env.company.currency_id,
            'product_uom_qty': self.product_uom_qty,
        }

    @api.depends('product_id')
    def _get_locations(self):
        for record in self:
            data_ids = []
            location_ids = []
            if record.product_id.type == 'product':
                stock_quant = record.env['stock.quant'].search([('product_id','=', record.product_id.id)])
                for quant in stock_quant:
                    if quant.available_quantity > 0 and quant.location_id.usage == 'internal':
                        location_ids.append(quant.location_id.id)
            else:
                locations = record.env['stock.location'].search([('usage', '=', 'internal')])
                for location in locations:
                    location_ids.append(location.id)
            record.filter_location_ids = [(6, 0, location_ids)]

    @api.depends('product_uom_qty','price_unit')
    def _amount_all(self):
        for rec in self:
            rec.price_subtotal = rec.product_uom_qty * rec.price_unit

    @api.onchange('product_id')
    def on_change_product(self):
        self.uom_id = self.product_id.uom_id.id
        self.price_unit = self.product_id.standard_price

    @api.model
    def default_get(self, fields):
        vals = super(MaintenanceEquipmentMaterialsList, self).default_get(fields)
        if self._context.get('is_scrap_location'):
            location_dest_id = self.env['stock.location'].search([('name','ilike','Scrap'), ('company_id', '=', self.env.company.id)],limit =1)
            if location_dest_id:
                vals['location_dest_id'] = location_dest_id.id
        return vals


    @api.depends('equipment_id')
    def _get_equipment_part_id_domain(self):
        self.equipment_part_id_domain = False
        if self.equipment_id.vehicle_parts_ids and self:
            self.equipment_part_id_domain = json.dumps([('id', 'in', self.equipment_id.vehicle_parts_ids.mapped('equipment_id').ids)])


class MaintenanceFrequency(models.Model):
    _name = 'maintenance.frequency'
    _description = 'Maintenance Frequency'

    frequency = fields.Float(string='Frequency')

class MaintenanceThreshold(models.Model):
    _name = 'maintenance.threshold'
    _description = 'Maintenance Threshold'

    threshold = fields.Float(string='Threshold')
    unit = fields.Char(string='Unit', readonly=True)
    maintenance_plan_id = fields.Many2one('maintenance.plan')

    @api.model
    def default_get(self, fields_list):
        defaults = super(MaintenanceThreshold, self).default_get(fields_list)
        if self._context.get('is_hourmeter_m_plan'):
            defaults['unit'] = 'hours'
        if self._context.get('is_odometer_m_plan'):
            defaults['unit'] = 'km'
        return defaults


class ToolsMaterialsList(models.Model):
    _name = 'tools.materials.list'
    _description = 'Tools Materials List'
    _order = 'maintenance_wo_id, maintenance_ro_id'

    product_id = fields.Many2one('product.product', string='Tools')
    uom_id = fields.Many2one('uom.uom', string='Tools')
    product_uom_qty = fields.Float(string='Quantity', default=1)
    notes = fields.Char('Notes')
    maintenance_plan_id = fields.Many2one('maintenance.plan')
    maintenance_wo_id = fields.Many2one('maintenance.work.order')
    maintenance_ro_id = fields.Many2one('maintenance.repair.order')
    equipment_id = fields.Many2one('maintenance.equipment', string='Tools')

    @api.onchange('product_id')
    def on_change_product(self):
        self.uom_id = self.product_id.uom_id.id

ToolsMaterialsList()

class MaintenanceWorkOrder(models.Model):
    _inherit = 'maintenance.work.order'

    maintenance_plan_parent_id = fields.Many2one('maintenance.plan', string="Maintenance Plan Parent")


class MaintenancePlan(models.Model):
    _name = 'maintenance.plan'
    _description = 'Maintenance Plan'
    _inherit = ['maintenance.plan','mail.thread', 'mail.activity.mixin']

    facility_area = fields.Many2one ('maintenance.facilities.area', string='Facilities Area')
    m_assignation_type = fields.Many2one('maintenance.assignation.type', string='Maintenance Assignation Type')
    remarks = fields.Text('Remarks')
    created_on = fields.Date(string='Created On', default=datetime.now(), readonly=True)
    user_id = fields.Many2one('res.users', 'Created By', required=True, default=lambda self: self.env.user, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch',default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)])
    approvalmatrix = fields.Many2one('approval.matrix.mp', string='Approval Matrix', compute='_compute_approvalmatrix')
    company_id = fields.Many2one("res.company", "Company", default=lambda self: self.env.user.company_id, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customers')

    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    meter_interval_number = fields.Integer(string='Odoo Meter Interval')
    frequency_interval_number = fields.Integer(string='Frequency')
    hm_interval_number = fields.Integer(string='HM Interval')
    task_check_list_ids = fields.One2many('plan.task.check.list','maintenance_plan_id',string='Task Checklist')
    maintenance_materials_list_ids = fields.One2many('maintenance.materials.list','maintenance_plan_id', string='Materials')
    tools_materials_list_ids = fields.One2many('tools.materials.list', 'maintenance_plan_id', string='Tools Materials')
    is_preventive_m_plan = fields.Boolean(string='Preventive Maintenance Plan', default=False)
    is_hourmeter_m_plan = fields.Boolean(string='Hour Meter Maintenance Plan', default=False)
    is_odometer_m_plan = fields.Boolean(string='Odo Meter Maintenance Plan', default=False)
    maintenance_category_ids = fields.Many2many('maintenance.equipment.category', string='Asset Category')
    maintenance_frequency_ids = fields.Float(string='Frequency')
    maintenance_threshold_ids = fields.One2many('maintenance.threshold', 'maintenance_plan_id', string='Asset Category')
    wo_ids = fields.Many2many('maintenance.repair.order', string='Repair Orders', compute="_compute_wo_count")
    workorder_ids = fields.One2many('maintenance.work.order', 'maintenance_plan_id', string='Maintenance Work Order')
    wo_count = fields.Integer(string='Workorder Count', compute='_compute_wo_count')
    maintenance_team_id = fields.Many2one("maintenance.teams", ondelete='restrict')
    next_wo_date = fields.Date(string='next work order')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('cancel', 'Cancelled'),
        ('done', 'Done'),
    ], string='State', readonly=True,default='draft')
    is_show_fac_area = fields.Boolean(string='Show Facility Area', compute="_compute_show_fac")
    maintenance_types = fields.Many2many('maintenance.type', string='Maintenance Types')

    approval_sequence = fields.Integer(string='Approval Sequence', default=0, readonly=True)
    approvers_id = fields.Many2many('res.users', string='Approvers')

    is_approval_matrix = fields.Boolean(string='Is Approval Matrix', compute='_compute_isapprovalmatrix')
    mwo_state = fields.Char(compute="compute_mwo_state", string="MWO State")
    duration = fields.Integer(string="Duration")
    calendar_action_boolean = fields.Boolean(string="Calendar Action")
    parent_record_boolean = fields.Boolean(string="Parent Record")
    color_id = fields.Integer(string="Color")
    parent_id = fields.Many2one('maintenance.plan', string="Parent Record")
    work_order_id = fields.Many2one('maintenance.work.order',string="Maintenance Work Order")

    def get_parent_colors(self):
        colors = {}
        unique_colors = ['#FF5733', '#33FF57', '#5733FF', '#33FFFF', '#FF33FF', '#FFFF33']
        for record in self:
            parent_id = record.parent_id.id
            if parent_id not in colors:
                colors[parent_id] = unique_colors[len(colors) % len(unique_colors)]
        return colors

    def update_calendar_colors(self):
        view_id = self.env.ref('equip3_asset_fms_operation.maintenance_plan_view_calendar')
        colors = self.get_parent_colors()
        view_id.write(
            {'arch': view_id.arch.replace('colors="{}"'.format(view_id.colors), 'colors="{}"'.format(colors))})

    @api.depends('work_order_id')
    def compute_mwo_state(self):
        for rec in self:
            state = []
            for mwo in rec.work_order_id:
                rec.mwo_state = ''
                vals = {'state': mwo.state_id}
                state.append(vals)
            # print('state',state)
            get_state = [x['state'] for x in state]
            rec.mwo_state = get_state


    @api.depends('branch_id')
    def _compute_isapprovalmatrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_mp')])
        approval =  IrConfigParam.get_param('equip3_asset_fms_operation.is_approval_matix_mp')
        for record in self:
            if is_there:
                record.is_approval_matrix = approval
            else:
                record.is_approval_matrix = False

    def action_move_print(self):
        return self.env.ref('equip3_asset_fms_report.action_report_preventive').report_action(self)

    @api.onchange('partner_id')
    def on_change_product(self):
        self._compute_show_fac()

    def _compute_show_fac(self):
        for rec in self:
            if rec.is_odometer_m_plan or rec.is_hourmeter_m_plan:
                rec.is_show_fac_area = True
            else:
                rec.is_show_fac_area = False

    def is_approval_matrix_defined(self):
        is_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('equip3_asset_fms_operation.is_approval_matix_mp')
        if is_approval_matrix == 'True':
            return True
        else:
            return False

    @api.depends('branch_id')
    def _compute_approvalmatrix(self):
        for rec in self:
            rec.approvalmatrix = self.env['approval.matrix.mp'].search([('branch_id', '=', rec.branch_id.id)], limit=1)

    def _compute_wo_count(self):
        for plan in self:
            if plan.parent_id:
                workorders = self.env['maintenance.work.order'].search([('maintenance_plan_id', '=', self.id)])
            else:
                workorders = self.env['maintenance.work.order'].search([('maintenance_plan_parent_id', '=', self.id)])

            plan.wo_ids = workorders.ids
            plan.wo_count = len(workorders)

    def action_move_active(self):
        if self.parent_record_boolean == False:
            self.calendar_action_boolean = True
            if not self.parent_id:
                dates = []
                if self.start_date and self.end_date and self.frequency_interval_number:
                    start_date_str = self.start_date.strftime("%Y-%m-%d")
                    end_date_str = self.end_date.strftime("%Y-%m-%d")
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                    frequency = timedelta(days=self.frequency_interval_number)
                    current_date = start_date
                    while current_date <= end_date:
                        dates.append(({'date': current_date.strftime("%Y-%m-%d")}))
                        current_date += frequency
                else:
                    self.duration = []
                for rec in dates:
                    new_name = self.name
                    frequency = 1
                    if rec['date']:
                        create_data = {
                            'parent_id': self.id,
                            'name': new_name,
                            'state': 'active',
                            'parent_record_boolean': True,
                            'partner_id': self.partner_id.id,
                            'facility_area': self.facility_area.id,
                            'user_id': self.user_id.id,
                            'maintenance_team_id': self.maintenance_team_id.id,
                            'm_assignation_type': self.m_assignation_type.id,
                            'next_wo_date': self.next_wo_date,
                            'branch_id': self.branch_id.id,
                            'start_date': rec['date'],
                            'end_date': rec['date'],
                            'frequency_interval_number': frequency,
                            'remarks': self.remarks,
                            'maintenance_category_ids': [(6, 0, self.maintenance_category_ids.ids)],
                            'maintenance_types': [(6, 0, self.maintenance_types.ids)],
                            'calendar_action_boolean': True}
                        main_plan_id = self.env['maintenance.plan'].create(create_data)
                        for line in self.task_check_list_ids:
                            temp_vals = {}
                            temp_vals['maintenance_plan_id'] = main_plan_id.id
                            temp_vals['equipment_id'] = line.equipment_id.id if line.equipment_id else False
                            temp_vals['vehicle_parts_ids'] = [(6, 0, line.vehicle_parts_ids.ids)]
                            temp_vals['task'] = line.task
                            self.env['plan.task.check.list'].create(temp_vals)
                        for line in self.maintenance_materials_list_ids:
                            temp_vals = {}
                            temp_vals['maintenance_plan_id'] = main_plan_id.id
                            temp_vals['product_id'] = line.equipment_id.id if line.equipment_id else False
                            temp_vals[
                                'parent_equipment_id'] = line.parent_equipment_id.id if line.parent_equipment_id else False
                            temp_vals[
                                'part_equipment_id'] = line.part_equipment_id.id if line.part_equipment_id else False
                            temp_vals['product_uom_qty'] = line.product_uom_qty
                            temp_vals['uom_id'] = line.uom_id.id if line.uom_id.id else False
                            temp_vals['location_id'] = line.location_id.id if line.location_id else False
                            temp_vals['location_dest_id'] = line.location_dest_id.id if line.location_dest_id else False
                            temp_vals['notes'] = line.notes
                            self.env['maintenance.materials.list'].create(temp_vals)
                        for line in self.tools_materials_list_ids:
                            temp_vals = {}
                            temp_vals['maintenance_plan_id'] = main_plan_id.id
                            temp_vals['product_id'] = line.product_id.id if line.equipment_id else False
                            temp_vals['product_uom_qty'] = line.product_uom_qty
                            temp_vals['uom_id'] = line.uom_id.id if line.uom_id.id else False
                            temp_vals['notes'] = line.notes
                            self.env['tools.materials.list'].create(temp_vals)


        if self.is_approval_matrix_defined():
            if self._check_approval_matrix_continue():
                for record in self:
                    if record.is_odometer_m_plan or record.is_hourmeter_m_plan:
                        categ_id = self.env['maintenance.equipment'].search([('category_id', 'in', record.maintenance_category_ids.ids)])
                        categ_id += record.task_check_list_ids.mapped('equipment_id').filtered(lambda r:r.id not in categ_id.ids)
                        if record.maintenance_frequency_ids > 0:
                            for rec in categ_id:
                                if record.is_odometer_m_plan:
                                    rec.frequency_odoometer_ids = [(0, 0, {'is_odometer_m_plan': record.id, 'floorodoo_value': 0.0})]
                                elif record.is_hourmeter_m_plan:
                                    rec.frequency_hourmeter_ids = [(0, 0, {'is_hourmeter_m_plan': record.id, 'floorhour_value': 0.0})]
                        if record.maintenance_threshold_ids:
                            for rec in categ_id:
                                if record.is_odometer_m_plan:
                                    rec.threshold_odoometer_ids = [(0, 0, {'is_odometer': record.id, 'last_threshold': 0.0})]
                                elif record.is_hourmeter_m_plan:
                                    rec.threshold_hourmeter_ids = [(0, 0, {'is_hourmeter': record.id, 'last_threshold': 0.0})]
                    record.write({'state':'active'})
        else:
            for record in self:
                if record.is_odometer_m_plan or record.is_hourmeter_m_plan:
                    categ_id = self.env['maintenance.equipment'].search([('category_id', 'in', record.maintenance_category_ids.ids)])
                    categ_id += record.task_check_list_ids.mapped('equipment_id').filtered(lambda r:r.id not in categ_id.ids)
                    if record.maintenance_frequency_ids > 0:
                        for rec in categ_id:
                            if record.is_odometer_m_plan:
                                rec.frequency_odoometer_ids = [(0, 0, {'is_odometer_m_plan': record.id, 'floorodoo_value': 0.0})]
                            elif record.is_hourmeter_m_plan:
                                rec.frequency_hourmeter_ids = [(0, 0, {'is_hourmeter_m_plan': record.id, 'floorhour_value': 0.0})]
                    if record.maintenance_threshold_ids:
                        for rec in categ_id:
                            if record.is_odometer_m_plan:
                                rec.threshold_odoometer_ids = [(0, 0, {'is_odometer': record.id, 'last_threshold': 0.0})]
                            elif record.is_hourmeter_m_plan:
                                rec.threshold_hourmeter_ids = [
                                    (0, 0, {'is_hourmeter': record.id, 'last_threshold': 0.0})]
                record.write({'state': 'active'})

    def _check_approval_matrix_continue(self):
        approval_line_ids = self.approvalmatrix.approval_matrix_mp_ids
        line = approval_line_ids.filtered(lambda x: x.sequence == self.approval_sequence)

        if self.env.user not in approval_line_ids.mapped('user_ids') or self.env.user not in line.mapped('user_ids'):
            raise ValidationError('You are not allowed to do this action. Please contact your system administrator for approval')

        total_approval_line = len(approval_line_ids)

        self.approvers_id = [(4, self.env.user.id)]
        self.activity_search(['mail.mail_activity_data_todo']).unlink()

        if len(self.approvers_id) >= line.min_approvers:
            self.approvers_id = [(5)]
            self.approval_sequence += 1

            if self.approval_sequence == total_approval_line:
                self.approval_sequence = 0
                return True

            for user in approval_line_ids.filtered(lambda x: x.sequence == self.approval_sequence).mapped('user_ids'):
                self.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo', user_id=user.id)
        return False

    def action_move_cancel(self):
        self.write({'state':'cancel'})

    def workorder_link(self):
        self.ensure_one()
        view_form_id = self.env.ref('equip3_asset_fms_operation.maintenance_work_order_view_form').id
        view_list_id = self.env.ref('equip3_asset_fms_operation.maintenance_work_order_view_tree').id
        if self.parent_id:
            action = {
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', self.workorder_ids.ids)],
                'view_mode': 'kanban,form',
                'name': _('Work Order'),
                'context': {'default_maintenance_plan_id': self.id},
                'res_model': 'maintenance.work.order',
            }
            if len(self.workorder_ids) == 1:
                action.update({'views': [(view_form_id, 'form')], 'res_id': self.workorder_ids.id})
            else:
                action['views'] = [(view_list_id, 'list'), (view_form_id, 'form')]
        else:
            action = {
                'type': 'ir.actions.act_window',
                'domain': [('maintenance_plan_parent_id', '=', self.id)],
                'view_mode': 'kanban,form',
                'name': _('Work Order'),
                'res_model': 'maintenance.work.order',
                'views': [(view_list_id, 'list'), (view_form_id, 'form')],
            }
        return action

    def unlink(self):
        for record in self:
            request_line_ids = self.env['request.line'].search(['|', ('is_odometer_m_plan', '=', record.id), ('is_hourmeter_m_plan', '=', record.id)])
            if request_line_ids:
                request_line_ids.unlink()
            threshold_line_ids = self.env['threshold.line'].search(['|', ('is_odometer', '=', record.id), ('is_hourmeter', '=', record.id)])
            if threshold_line_ids:
                threshold_line_ids.unlink()
            maintenance_plan = self.env['maintenance.plan'].search([('parent_id','=', record.id)])
            if maintenance_plan:
                maintenance_plan.unlink()
        return super(MaintenancePlan, self).unlink()

    @api.model
    def default_get(self, fields_list):
        defaults = super(MaintenancePlan, self).default_get(fields_list)
        if self._context.get('categ_id'):
            defaults['maintenance_category_ids'] = [(6, 0, [self._context.get('categ_id')])]
        return defaults

    def get_material_list(self):
        for record in self:
            equipment_ids = record.task_check_list_ids.filtered(lambda r: not r.already_compute).mapped('equipment_id')
            materials = record.env['maintenance.equipment.materials.list'].read_group(
                domain=[('equipment_id', 'in', equipment_ids.ids)],
                fields=['uom_id', 'product_id', 'product_uom_qty', 'location_id', 'location_dest_id', 'equipment_id', 'equipment_part_id', 'price_unit'],
                groupby=['uom_id', 'product_id', 'location_id', 'location_dest_id', 'equipment_id', 'equipment_part_id', 'price_unit'],
                lazy=False)

            existing_materials = record.maintenance_materials_list_ids.mapped('parent_equipment_id')

            materials_to_create = []
            for material in materials:
                product_id = self.env['product.product'].browse(material.get('product_id')[0])
                parent_equipment_id = self.env['maintenance.equipment'].browse(material.get('equipment_id')[0])
                if parent_equipment_id not in existing_materials:
                    location_id = self.env['stock.location'].browse(material.get('location_id')[0])
                    location_dest_id = self.env['stock.location'].browse(material.get('location_dest_id')[0])
                    material_data = {
                        'product_id': product_id.id,
                        'parent_equipment_id': material.get('equipment_id')[0],
                        'part_equipment_id': material.get('equipment_part_id')[0] if material.get('equipment_part_id') else False,
                        'product_uom_qty': material.get('product_uom_qty'),
                        'uom_id': material.get('uom_id')[0],
                        'location_id': location_id.id,
                        'location_dest_id': location_dest_id.id,
                        'price_unit': material.get('price_unit'),
                    }
                    materials_to_create.append((0, 0, material_data))

            try:
                if materials_to_create:
                    # print("➡ materials_to_create :", materials_to_create)
                    record.write({'maintenance_materials_list_ids': materials_to_create})
                record.task_check_list_ids.write({'already_compute': True})
            except Exception as e:
                pass


    @api.model
    def create(self, vals):
        res = super(MaintenancePlan, self).create(vals)
        res.create_workorder()
        res.get_material_list()
        return res

    def write(self, vals):
        res = super(MaintenancePlan, self).write(vals)
        self.get_material_list()
        if vals.get('state') == 'active':
            if self.start_date <= self.get_today():
                self.next_wo_date = self.get_today()
                self.create_workorder()
            elif self.start_date > self.get_today():
                self.next_wo_date = self.start_date
        return res

    def create_workorder(self):
        asset_lst = []
        plan_data = self.env['maintenance.plan'].search([('is_preventive_m_plan', '=', True), ('start_date', '!=', False), ('end_date', '!=', False), ('frequency_interval_number', '!=', False), ('parent_id', '!=', False)])
        for plan in plan_data:
            work_order = self.env['maintenance.work.order'].search([('maintenance_plan_id', '=', plan.id), ('startdate', '=', self.get_today())])
            if not work_order and plan.state == 'active':
                if plan.start_date <= self.get_today() and plan.end_date >= self.get_today():
                    if plan.start_date == self.get_today() or plan.next_wo_date == self.get_today():
                        work_order_id = self.env['maintenance.work.order'].create({
                            'partner_id': plan.partner_id.id,
                            'maintenance_plan_parent_id': plan.parent_id.id,
                            'facility': plan.facility_area.id,
                            'user_id': plan.user_id.id,
                            'maintenanceteam': plan.maintenance_team_id.id,
                            'maintenanceassign': plan.m_assignation_type.id,
                            'branch_id': plan.branch_id.id,
                            'company_id': plan.company_id.id,
                            'remarks': plan.remarks,
                            'maintenance_plan_id': plan.id,
                            'ref': plan.name,
                            'startdate': self.get_today(),
                            'enddate': self.get_today(),
                            'maintenance_types': [(6, 0, plan.maintenance_types.ids)],
                            'task_check_list_ids': [(6, 0, plan.parent_id.task_check_list_ids.ids)],
                            'maintenance_materials_list_ids': [(6, 0, plan.parent_id.maintenance_materials_list_ids.ids)],
                            'tools_materials_list_ids': [(6, 0, plan.parent_id.tools_materials_list_ids.ids)],
                        })
                        if work_order_id:
                            # plan_data = self.env['maintenance.plan'].search([('parent_id', '=', self.id),('start_date', '=',self.start_date)])
                            # for plan in plan_data:
                            #     plan.work_order_id = work_order_id
                            work_order_id.maintenance_plan_id.work_order_id = work_order_id
                        for asset in plan.maintenance_category_ids:
                            asset_lst = asset.equipment_ids.ids
                            for eq_id in asset_lst:
                                work_order_id.task_check_list_ids = [(0, 0, {
                                    'equipment_id': eq_id,
                                })]
                        if work_order_id:
                            plan.next_wo_date = self.get_today() + timedelta(days=plan.frequency_interval_number)
                            if plan.next_wo_date > plan.end_date:
                                plan.state = 'done'

    def get_today(self):
        tz = pytz.timezone('Asia/Singapore')
        today = datetime.now(tz).date()
        return today

    def add_threshold_action(self):
        view_id = self.env.ref('equip3_asset_fms_operation.create_multiple_threshold_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Mutiple Threshold'),
            'res_model': 'multiple.threshold.wizard',
            'target': 'new',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'context': {}
        }

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Maintenance Plan'),
            'template': '/equip3_asset_fms_operation/static/xls/maintenance_plan_template.xls'
        }]

MaintenancePlan()


class MaintenanceEquipmentCategory(models.Model):
    _inherit = 'maintenance.equipment.category'

    # def name_get(self):
    #     result = []
    #     result_all = []
    #     maintenanceplan = self.env['maintenance.plan'].search([('id', '=', self._context.get('active_id'))])
    #     for rec in self:
    #         name = rec.name
    #         result_all += [(rec.id, name)]
    #         if rec.equipment_ids:
    #             equ_lst = rec.equipment_ids.mapped('vehicle_checkbox')
    #             if False not in equ_lst:
    #                 result += [(rec.id, name)]
    #         result = list(set(result))
    #         result_all = list(set(result_all))
    #     if self._context.get('is_odometer_m_plan'):
    #         return result
    #     else:
    #         return result_all

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    maintenance_materials_list_ids = fields.One2many('maintenance.equipment.materials.list','equipment_id', string='Materials')
    tools_materials_list_ids = fields.One2many('tools.materials.list','equipment_id', string='Tools')
    is_running_state = fields.Boolean('Running State',compute='get_running_state')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(MaintenanceEquipment, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        if 'toolbar' in result:
            debug_mode = request.session.debug
            regenerate_qrcode = self.env.ref('equip3_asset_fms_masterdata.regenerate_qrcode')
            if not debug_mode:
                result['toolbar']['action'] = [
                    action for action in result['toolbar'].get('action', [])
                    if action['id'] != regenerate_qrcode.id
                ]
            result['toolbar']['print'] = [
                x for x in result['toolbar'].get('print', [])
                if x['id'] not in [
                    self.env.ref('equip3_asset_fms_masterdata.report_maintenance_equipment_asset_barcode').id,
                    self.env.ref('equip3_asset_fms_masterdata.report_maintenance_equipment_qrcode').id
                ]
            ]
        return result

    def get_running_state(self):
        for rec in self:
            if rec.account_asset_id and rec.account_asset_id.state=='open':
                rec.is_running_state = True
            else:
                rec.is_running_state = False

    def set_to_close_changed(self):
        self.state = 'scrapped'
        return self.account_asset_id.set_to_close()


    def show_button_asset_popup(self):
        if self.account_asset_id:
            return {
                'name': 'Sale',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'asset.asset.sale',
                'context': {'asset_id': self.account_asset_id.id},
                'type': 'ir.actions.act_window',
                'target': 'new',

            }
