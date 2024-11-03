# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree


# TODO : need to optimize function inside this class
class VariableTemplate(models.Model):
    _name = 'variable.template'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Variable'
    _check_company_auto = True
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(VariableTemplate, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        root = etree.fromstring(res['arch'])
        if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer'):
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group('abs_construction_management.group_construction_manager'):
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

    @api.onchange('variable_subcon')
    def _onchange_variable_subcon(self):
        context = dict(self.env.context) or {}
        if context.get('variable_subcon'):
            self.variable_subcon = True
    
    @api.depends('material_variable_ids.subtotal', 'labour_variable_ids.subtotal', 
                 'subcon_variable_ids.subtotal', 'overhead_variable_ids.subtotal', 
                 'equipment_variable_ids.subtotal', 'service_variable_ids.subtotal',
                 'asset_variable_ids.subtotal')
    def _calculate_total(self):
        total_job_cost = 0.0
        for order in self:
            if order.material_variable_ids : 
                for line in order.material_variable_ids:
                    material_price =  (line.quantity * line.unit_price)
                    order.total_variable_material += material_price
                    total_job_cost += material_price

            else : 

                order.total_variable_material = 0

            if order.labour_variable_ids :
                for line in order.labour_variable_ids:
                    labour_price =  (line.quantity * line.unit_price) 
                    order.total_variable_labour += labour_price
                    total_job_cost += labour_price
            else :

                order.total_variable_labour = 0

            if order.overhead_variable_ids: 
                for line in order.overhead_variable_ids:
                    overhead_price =  (line.quantity * line.unit_price) 
                    order.total_variable_overhead += overhead_price
                    total_job_cost += overhead_price

            else :

                order.total_variable_overhead = 0
            
            if order.subcon_variable_ids :
                for line in order.subcon_variable_ids:
                    subcon_price =  (line.quantity * line.unit_price) 
                    order.total_variable_subcon += subcon_price
                    total_job_cost += subcon_price
            else :

                order.total_variable_subcon = 0

            if order.service_variable_ids :
                for line in order.service_variable_ids:
                    service_price =  (line.quantity * line.unit_price) 
                    order.total_variable_service += service_price
                    total_job_cost += service_price
            else :

                order.total_variable_service = 0

            if order.equipment_variable_ids :
                for line in order.equipment_variable_ids:
                    equipment_price =  (line.quantity * line.unit_price) 
                    order.total_variable_equipment += equipment_price
                    total_job_cost += equipment_price
            else :

                order.total_variable_equipment = 0

            if order.asset_variable_ids :
                for line in order.asset_variable_ids:
                    asset_price =  (line.quantity * line.unit_price) 
                    order.total_variable_internal_asset += asset_price
                    total_job_cost += asset_price
            else :

                order.total_variable_internal_asset = 0

            order.total_variable_asset = order.total_variable_equipment + order.total_variable_internal_asset
            order.total_variable = total_job_cost

        return

    @api.constrains('material_variable_ids', 'labour_variable_ids', 'overhead_variable_ids',
                    'equipment_variable_ids', 'asset_variable_ids', 'subcon_variable_ids')
    def _check_estimation_lines(self):
        for rec in self:
            if len(rec.material_variable_ids) == len(rec.labour_variable_ids) == len(
                    rec.overhead_variable_ids) == len(rec.asset_variable_ids) == len(
                rec.equipment_variable_ids) == len(rec.subcon_variable_ids) == 0:
                raise ValidationError(
                    _('The Estimation tables are empty. Please add at least 1 product for estimation.'))

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id
            line.company_id = res_user_id.company_id

    @api.onchange('variable_subcon')
    def onchange_variable_subcon(self):
        if self.variable_subcon == True:
            self.subcon_variable_ids = False
        else:
            self.service_variable_ids = False

    @api.constrains('material_variable_ids')
    def _check_material_variable_ids(self):
        for record in self:
            if record.material_variable_ids:
                for line in record.material_variable_ids:
                    if line.unit_price <= 0 :
                        raise ValidationError(_('In tab material, the unit price of product "%s" should be greater than 0.'%((line.product_id.name))))
                    elif line.quantity <= 0 :
                        raise ValidationError(_('In tab material, the quantity of product "%s" should be greater than 0.'%((line.product_id.name))))


    @api.constrains('labour_variable_ids')
    def _check_labour_variable_ids(self):
        for record in self:
            if record.labour_variable_ids:
                for line in record.labour_variable_ids:
                    if line.unit_price <= 0:
                        raise ValidationError(_('In tab labour, the unit price of product "%s" should be greater than 0.'%((line.product_id.name))))
                    elif line.quantity <= 0 :
                        raise ValidationError(_('In tab labour, the quantity of product "%s" should be greater than 0.'%((line.product_id.name))))


    @api.constrains('overhead_variable_ids')
    def _check_overhead_variable_ids(self):
        for record in self:
            if record.overhead_variable_ids:
                for line in record.overhead_variable_ids:
                    if line.unit_price <= 0:
                        raise ValidationError(_('In tab overhead, the unit price of product "%s" should be greater than 0.'%((line.product_id.name))))
                    elif line.quantity <= 0 :
                        raise ValidationError(_('In tab overhead, the quantity of product "%s" should be greater than 0.'%((line.product_id.name))))

    @api.constrains('equipment_variable_ids')
    def _check_equipment_variable_ids(self):
        for record in self:
            if record.equipment_variable_ids:
                for line in record.equipment_variable_ids:
                    if line.unit_price <= 0:
                        raise ValidationError(_('In tab equipment, the unit price of product "%s" should be greater than 0.'%((line.product_id.name))))
                    elif line.quantity <= 0 :
                        raise ValidationError(_('In tab equipment, the quantity of product "%s" should be greater than 0.'%((line.product_id.name))))

    @api.constrains('asset_variable_ids')
    def _check_asset_variable_ids(self):
        for record in self:
            if record.asset_variable_ids:
                for line in record.asset_variable_ids:
                    if line.unit_price == 0:
                        raise ValidationError(_('In tab internal asset, the unit price of asset "%s" should be greater than 0.'%((line.asset_id.name))))
                    elif line.quantity <= 0 :
                        raise ValidationError(_('In tab internal, the quantity of product "%s" should be greater than 0.'%((line.asset_id.name))))

    @api.constrains('service_variable_ids')
    def _check_service_variable_ids(self):
        for record in self:
            if record.service_variable_ids:
                for line in record.service_variable_ids:
                    if line.unit_price <= 0:
                        raise ValidationError(_('In tab service, the unit price of product "%s" should be greater than 0.'%((line.product_id.name))))
                    elif line.quantity <= 0 :
                        raise ValidationError(_('In tab service, the quantity of product "%s" should be greater than 0.'%((line.product_id.name))))

    @api.constrains('subcon_variable_ids')
    def _check_subcon_variable_ids(self):
        for record in self:
            if record.subcon_variable_ids:
                for line in record.subcon_variable_ids:
                    if line.unit_price <= 0:
                        raise ValidationError(_('In tab subcon, the unit price of job subcon "%s" should be greater than 0.'%((line.variable.name))))
                    elif line.quantity <= 0 :
                        raise ValidationError(_('In tab subcon, the quantity of product "%s" should be greater than 0.'%((line.variable.name))))   

    @api.onchange('material_variable_ids')
    def _check_exist_product_id_material(self):
        exist_group_list = []
        for line in self.material_variable_ids:
            if line.product_id.id in exist_group_list:
                raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
            exist_group_list.append(line.product_id.id)
                 
    
    @api.onchange('labour_variable_ids')
    def _check_exist_product_id_labour(self):
        exist_group_list = []
        for line in self.labour_variable_ids:
            if line.product_id.id in exist_group_list:
                raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
            exist_group_list.append(line.product_id.id)

    @api.onchange('overhead_variable_ids')
    def _check_exist_product_id_overhead(self):
        exist_group_list = []
        for line in self.overhead_variable_ids:
            if line.product_id.id in exist_group_list:
                raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
            exist_group_list.append(line.product_id.id)

    @api.onchange('equipment_variable_ids')
    def _check_exist_product_id_equipment(self):
        exist_group_list = []
        for line in self.equipment_variable_ids:
            if line.product_id.id in exist_group_list:
                raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
            exist_group_list.append(line.product_id.id)
    
    @api.onchange('asset_variable_ids')
    def _check_exist_group_of_product_asset(self):
        exist_group_list = []
        for line in self.asset_variable_ids:
            if line.asset_id.id in exist_group_list:
                raise ValidationError(_('The Asset "%s" already exists, please change the selected Asset.'%((line.asset_id.name))))
            exist_group_list.append(line.asset_id.id)

    @api.onchange('service_variable_ids')
    def _check_exist_product_id_service(self):
        exist_group_list = []
        for line in self.service_variable_ids:
            if line.product_id.id in exist_group_list:
                raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
            exist_group_list.append(line.product_id.id)

    @api.onchange('subcon_variable_ids')
    def _check_exist_subcon(self):
        exist_subcon_list = []
        for line in self.subcon_variable_ids:
            if line.variable.name in exist_subcon_list:
                raise ValidationError(_('The subcon "%s" already exists, please change the subcon.'%((line.variable.name))))
            exist_subcon_list.append(line.variable.name)

    @api.constrains('name')
    def _check_existing_record(self):
        for record in self:
            name_id = self.env['variable.template'].search(
                [('name', '=', record.name), ('variable_subcon', '=', record.variable_subcon)])
            if len(name_id) > 1:
                if self.variable_subcon == False:
                    raise ValidationError(
                        f'The Variable name already exists, which is the same as the previous Variable name.\nPlease change the Variable name.')
                elif self.variable_subcon == True:
                    raise ValidationError(
                        f'The Subcon name already exists, which is the same as the previous Subcon name.\nPlease change the Subcon name.')    

                    
    active = fields.Boolean(string='Active', default=True)
    name = fields.Char("Variable Name", tracking=True)
    external_id = fields.Char(string='External ID')
    variable_subcon = fields.Boolean(string="Variable Subcon", default=False)
    variable_uom = fields.Many2one('uom.uom', required=True, string="Unit of Measure")
    total_variable = fields.Monetary(string="Total Variable", default=0.0, readonly=True, compute="_calculate_total")
    company_currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, readonly=True,
                                 default=lambda self: self.env.company)
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                domain=lambda self: [('id', 'in', self.env.branches.ids),('company_id','=', self.env.company.id)])
    created_by = fields.Many2one("res.users", string="Created By", default=lambda self: self.env.uid, readonly=True)
    created_date = fields.Date("Creation Date", default=fields.Date.today, readonly=True)

    material_variable_ids = fields.One2many('material.variable', 'material_id', string="Material")
    labour_variable_ids = fields.One2many('labour.variable', 'labour_id', string="Labour")
    subcon_variable_ids = fields.One2many('subcon.variable', 'subcon_id', string="Subcon")
    overhead_variable_ids = fields.One2many('overhead.variable', 'overhead_id', string="Overhead")
    equipment_variable_ids = fields.One2many('equipment.variable', 'equipment_id', string="Equipment")
    service_variable_ids = fields.One2many('service.variable', 'service_id', string="Service")
    asset_variable_ids = fields.One2many('asset.variable', 'asset_job_id', string="Asset")
    
    total_variable_material = fields.Monetary(compute='_calculate_total', string="Total Material", default=0.0, readonly=True)
    total_variable_labour = fields.Monetary(compute='_calculate_total', string="Total Labour", default=0.0, readonly=True)
    total_variable_subcon = fields.Monetary(compute='_calculate_total', string="Total Subcon", default=0.0, readonly=True)
    total_variable_overhead = fields.Monetary(compute='_calculate_total', string="Total Overhead", default=0.0, readonly=True)
    total_variable_equipment = fields.Monetary(compute='_calculate_total', string="Total Equipment", default=0.0, readonly=True)
    total_variable_service = fields.Monetary(compute='_calculate_total', string="Total Service", default=0.0, readonly=True)
    total_variable_internal_asset = fields.Monetary(string='Total Internal Asset', default=0.0, compute="_calculate_total")
    total_variable_asset = fields.Monetary(string='Total Asset', default=0.0, compute="_calculate_total")


class MaterialEstimation(models.Model):
    _name = 'material.variable'
    _description = 'Material Variable'
    _order = 'sequence'
    _check_company_auto = True

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = 1.0
            self.unit_price = False

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

    @api.depends('material_id.material_variable_ids', 'material_id.material_variable_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.material_id.material_variable_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.quantity == 0:
                raise ValidationError('Quantity cannot be 0.')
            # elif line.unit_price <= 0:
            #     raise ValidationError(_('In material, The Product "%s" unit price should be greater than 0.'%((line.product_id.name))))
            else:
                price =  (line.quantity * line.unit_price) 
                line.subtotal = price

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'product')]}
            }

    material_id = fields.Many2one('variable.template', string="Variable")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True, domain="[('company_id','=',parent.company_id)]")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='material_id.company_id', string='Company', readonly=True)
    description = fields.Text(string="Description", required=True)
    quantity = fields.Float(string="Quantity", default=1.0)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure", domain="[('category_id', '=', product_uom_category_id)]")
    unit_price = fields.Float(string="Unit Price", default=0.0)
    subtotal = fields.Float(readonly=True, string="Subtotal")
    currency_id = fields.Many2one('res.currency', compute='get_currency_id', string="Currency")


class LabourEstimation(models.Model):
    _name = 'labour.variable'
    _description = 'Labour Variable'
    _order = 'sequence'
    _check_company_auto = True

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.contractors = 1.0
            self.time = 1.0
            self.uom_id = self.product_id.uom_id.id
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.contractors = 1.0
            self.time = 1.0
            self.description = False
            self.uom_id = False
            self.unit_price = False

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

    @api.depends('labour_id.labour_variable_ids', 'labour_id.labour_variable_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.labour_id.labour_variable_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('contractors', 'time', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.contractors == 0:
                raise ValidationError('Contractor cannot be 0.')
            # elif line.unit_price <= 0.0:
            #     raise ValidationError("The Unit of Price cannot be 0.")
            elif line.time == 0:
                raise ValidationError('Time cannot be 0.')
            else:
                quantity = (line.contractors * line.time)
                line.quantity = quantity
                price = (quantity * line.unit_price)
                line.subtotal = price

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', 'in', ['product', 'service'])]}
            }

    labour_id = fields.Many2one('variable.template', string="Variable")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True, domain="[('company_id','=',parent.company_id)]")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='labour_id.company_id', string='Company', readonly=True)
    description = fields.Text(string="Description")
    quantity = fields.Float(string="Quantity")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure", domain="[('category_id', '=', product_uom_category_id)]")
    unit_price = fields.Float(string="Unit Price", default=0.0, required=True)
    subtotal = fields.Float(readonly=True, string="Subtotal")
    currency_id = fields.Many2one('res.currency', compute='get_currency_id', string="Currency")
    contractors = fields.Integer('Contractors', required=True, default=1.0)
    time = fields.Float('Time', required=True, default=1.0)


class SubconEstimation(models.Model):
    _name = 'subcon.variable'
    _description = 'Subcon Variable'
    _order = 'sequence'
    _check_company_auto = True

    subcon_id = fields.Many2one('variable.template', string="Variable")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    variable = fields.Many2one('variable.template', string="Subcon",
               domain="[('variable_subcon', '=', True), ('company_id', '=', parent.company_id)]")
    company_id = fields.Many2one(related='subcon_id.company_id', string='Company', readonly=True)
    description = fields.Text(string="Description", required=True)
    quantity = fields.Float(string="Quantity", default=1.0)
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure")
    unit_price = fields.Float(string="Unit Price", default=0.0)
    subtotal = fields.Float(readonly=True, string="Subtotal")
    currency_id = fields.Many2one('res.currency', compute='get_currency_id', string="Currency")

    @api.onchange('variable')
    def onchange_variable(self):
        if self.variable:
            for res in self.variable:
                self.description = res.name
                self.uom_id = res.variable_uom.id
                self.quantity = 1.0
                self.unit_price = res.total_variable
        else:
            self.description = False
            self.uom_id = False
            self.quantity = 1.0
            self.unit_price = 0.0

    @api.onchange('variable')
    def onchange_variable_2(self):
        if self.variable:
            for res in self.variable:
                self.update({'unit_price': res.total_variable})
        else:
            self.update({'unit_price': 0.0})
    
    @api.depends('subcon_id.subcon_variable_ids', 'subcon_id.subcon_variable_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.subcon_id.subcon_variable_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.quantity == 0:
                raise ValidationError('Quantity cannot be 0.')
            # elif line.unit_price <= 0:
            #     raise ValidationError(_('In subcon, The Product "%s" unit price should be greater than 0.'%((line.variable.name))))
            else:
                price =  (line.quantity * line.unit_price) 
                line.subtotal = price


class OverheadEstimation(models.Model):
    _name = 'overhead.variable'
    _description = 'Overhead Variable'
    _order = 'sequence'
    _check_company_auto = True

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = 1.0
            self.unit_price = False

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
    
    @api.depends('overhead_id.overhead_variable_ids', 'overhead_id.overhead_variable_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.overhead_id.overhead_variable_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.quantity == 0:
                raise ValidationError('Quantity cannot be 0.')
            # elif line.unit_price <= 0:
            #     raise ValidationError(_('In overhead, The Product "%s" unit price should be greater than 0.'%((line.product_id.name))))
            else:
                price =  (line.quantity * line.unit_price) 
                line.subtotal = price

    @api.onchange('overhead_catagory', 'group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            if rec.overhead_catagory in ('product','fuel'):
                return {
                    'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'product')]}
                }
            else:
                return {
                    'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'consu')]}
                }

    overhead_id = fields.Many2one('variable.template', string="Variable")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True, domain="[('company_id','=',parent.company_id)]")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='overhead_id.company_id', string='Company', readonly=True)
    description = fields.Text(string="Description", required=True)
    quantity = fields.Float(string="Quantity", default=1.0)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure", domain="[('category_id', '=', product_uom_category_id)]")
    unit_price = fields.Float(string="Unit Price", default=0.0)
    subtotal = fields.Float(readonly=True, string="Subtotal")
    currency_id = fields.Many2one('res.currency', compute='get_currency_id', string="Currency")
    overhead_catagory = fields.Selection([
        ('product', 'Product'),
        ('petty cash', 'Petty Cash'),
        ('cash advance', 'Cash Advance'),
        ('fuel', 'Fuel'),
    ], string='Overhead Catagory', required=False)


class EquipmentEstimation(models.Model):
    _name = 'equipment.variable'
    _description = 'Equipment Variable'
    _order = 'sequence'
    _check_company_auto = True

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = 1.0
            self.unit_price = False

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
    
    @api.depends('equipment_id.equipment_variable_ids', 'equipment_id.equipment_variable_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.equipment_id.equipment_variable_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.quantity == 0:
                raise ValidationError('Quantity cannot be 0.')
            # elif line.unit_price <= 0:
            #     raise ValidationError(_('In equipment, The Product "%s" unit price should be greater than 0.'%((line.product_id.name))))
            else:
                price =  (line.quantity * line.unit_price) 
                line.subtotal = price

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'asset')]}
            }
    
    equipment_id = fields.Many2one('variable.template', string="Variable")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True, domain="[('company_id','=',parent.company_id)]")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='equipment_id.company_id', string='Company', readonly=True)
    description = fields.Text(string="Description", required=True)
    quantity = fields.Float(string="Quantity", default=1.0)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure", domain="[('category_id', '=', product_uom_category_id)]")
    unit_price = fields.Float(string="Unit Price", default=0.0)
    subtotal = fields.Float(readonly=True, string="Subtotal")
    currency_id = fields.Many2one('res.currency', compute='get_currency_id', string="Currency")


class ServiceEstimation(models.Model):
    _name = 'service.variable'
    _description = 'Service Variable'
    _order = 'sequence'
    _check_company_auto = True

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = 1.0
            self.unit_price = False

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

    @api.depends('service_id.service_variable_ids', 'service_id.service_variable_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.service_id.service_variable_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.quantity == 0:
                raise ValidationError('Quantity cannot be 0.')
            # elif line.unit_price <= 0:
            #     raise ValidationError(_('In service, The Product "%s" unit price should be greater than 0.'%((line.product_id.name))))
            else:
                price =  (line.quantity * line.unit_price) 
                line.subtotal = price

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'service')]}
            }

    service_id = fields.Many2one('variable.template', string="Variable")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True, domain="[('company_id','=',parent.company_id)]")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='service_id.company_id', string='Company', readonly=True)
    description = fields.Text(string="Description", required=True)
    quantity = fields.Float(string="Quantity", default=1.0)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure", domain="[('category_id', '=', product_uom_category_id)]")
    unit_price = fields.Float(string="Unit Price", default=0.0)
    subtotal = fields.Float(readonly=True, string="Subtotal")
    currency_id = fields.Many2one('res.currency', compute='get_currency_id', string="Currency")


class InternalAssetsEstimation(models.Model):
    _name = 'asset.variable'
    _description = 'Internal Asset Variable'
    _order = 'sequence'
    _check_company_auto = True

    asset_job_id = fields.Many2one('variable.template', string="Variable")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category', required=True)
    asset_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    description = fields.Text(string="Description")
    quantity = fields.Float('Quantity', default=1)
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure")
    unit_price = fields.Float(string='Unit Price', default=0.0)
    subtotal = fields.Float(string='Subtotal', readonly=True)
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='asset_job_id.company_id', string='Company', readonly=True)

    @api.onchange('asset_id')
    def _onchange_uom_asset_id(self):
        for rec in self:
            domain = self.env['uom.category'].search([('name', '=', 'Working Time')],limit=1)
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

    @api.depends('asset_job_id.asset_variable_ids', 'asset_job_id.asset_variable_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.asset_job_id.asset_variable_ids:
                no += 1
                l.sr_no = no

    @api.onchange('project_scope')
    def onchange_product_id(self):
        if self.project_scope_line_id:
            section = self.env['section.line'].sudo().search([('project_scope.id', '=', self.project_scope_line_id.id)])
            self.section_name = section.id

    @api.onchange('asset_category_id')
    def onchange_asset_category(self):
        if self.asset_category_id:
            asset = self.env['maintenance.equipment'].sudo().search(
                [('category_id.id', '=', self.asset_category_id.id)])
            # self.asset_id = asset.id
            return {'domain': {'asset_id': [('id', 'in', asset.ids)]}}

    @api.onchange('quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.quantity == 0:
                raise ValidationError('Quantity cannot be 0.')
            # elif line.unit_price <= 0:
            #     raise ValidationError(_('In internal asset, The Product "%s" unit price should be greater than 0.'%((line.asset_id.name))))
            else:
                price = (line.quantity * line.unit_price)
                line.subtotal = price

    @api.onchange('asset_id')
    def onchange_asset_id(self):
        if self.asset_id:
            self.description = self.asset_id.display_name
            self.quantity = 1.0
        else:
            self.description = False
            self.quantity = 1.0

    @api.onchange('asset_category_id')
    def _onchange_asset_category_handling(self):
        if self._origin.asset_category_id._origin.id:
            if self._origin.asset_category_id._origin.id != self.asset_category_id.id:
                self.update({
                    'asset_id': False,
                })
        else:
            self.update({
                'asset_id': False,
            })

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id
