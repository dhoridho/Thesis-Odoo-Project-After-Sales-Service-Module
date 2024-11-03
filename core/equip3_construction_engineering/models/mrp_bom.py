from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'
	
    labour_ids = fields.One2many('mrp.bom.labour','bom_id')
    overhead_ids = fields.One2many('mrp.bom.overhead','bom_id')
    equipment_ids = fields.One2many('mrp.bom.equipment','bom_id')
    asset_ids = fields.One2many('mrp.bom.asset','bom_id')
    variable_ref = fields.Many2one('variable.template','Variable')
    name = fields.Char(string="Finish Good")

    @api.onchange('product_tmpl_id')
    def onchange_name(self):
        if self.product_tmpl_id:
            self.name = self.product_tmpl_id.display_name
    
    def _prepare_subcon(self, res, name):
        return {
            "name" : name,
            "variable_uom": res.product_uom_id.id,
            "branch_id": res.branch.id,
            "variable_subcon": True,
            "is_manuf": True,
            "bom_id": res.id,
            "total_variable": res.forecast_cost,
        }

    def create_subcon(self, res, name):
        values = res._prepare_subcon(res, name)
        variable = res.env['variable.template'].create(values)
        res.variable_ref = variable.id

    @api.onchange('can_be_subcontracted')
    def subcontracted(self):
        name = False
        for res in self:
            if res.can_be_subcontracted == True:
                if res.product_tmpl_id:
                    name = 'BOM ' + res.product_tmpl_id.display_name
                else:
                    raise ValidationError("Please input the Finish Good.")
                variable = self.env['variable.template'].search([('name', '=', name), ('variable_subcon', '=', True)])
                if variable:
                    res.variable_ref = variable.id
                    variable.total_variable = res.forecast_cost
                else:
                    res.create_subcon(res, name)
            elif res.can_be_subcontracted == False:
                res.variable_ref = False

    @api.onchange('bom_line_ids')
    def _check_exist_material(self):
        exist_material_list = []
        material = False
        for line in self.bom_line_ids:
            material = line.group_of_product.name + line.product_id.name + line.operation_two_id.name
            if material in exist_material_list:
                raise ValidationError(_('The product "%s" already exists in "%s" group of product on "%s" operation, please change the product!'%((line.product_id.name), (line.group_of_product.name), (line.operation_two_id.name))))
            exist_material_list.append(material)

    @api.onchange('labour_ids')
    def _check_exist_labour(self):
        exist_labour_list = []
        labour = False
        for line in self.labour_ids:
            labour = line.group_of_product.name + line.product_id.name + line.operation_two_id.name
            if labour in exist_labour_list:
                raise ValidationError(_('The product "%s" already exists in "%s" group of product, please change the product!'%((line.product_id.name), (line.group_of_product.name), (line.operation_two_id.name))))
            exist_labour_list.append(labour)

    @api.onchange('overhead_ids')
    def _check_exist_overhead(self):
        exist_overhead_list = []
        overhead = False
        for line in self.overhead_ids:
            overhead = line.group_of_product.name + line.product_id.name + line.operation_two_id.name
            if overhead in exist_overhead_list:
                raise ValidationError(_('The product "%s" already exists in "%s" group of product and , please change the product!'%((line.product_id.name), (line.group_of_product.name), (line.operation_two_ids.name))))
            exist_overhead_list.append(overhead)

    @api.onchange('equipment_ids')
    def _check_exist_equipment(self):
        exist_equipment_list = []
        equipment = False
        for line in self.equipment_ids:
            equipment = line.group_of_product.name + line.product_id.name + line.operation_two_id.name
            if equipment in exist_equipment_list:
                raise ValidationError(_('The product "%s" already exists in "%s" group of product, please change the product!'%((line.product_id.name), (line.group_of_product.name), (line.operation_two_id.name))))
            exist_equipment_list.append(equipment)

    @api.onchange('asset_ids')
    def _check_exist_equipment(self):
        exist_asset_list = []
        asset = False
        for line in self.asset_ids:
            asset = line.asset_category_id.name + line.asset_id.name + line.operation_two_id.name
            if asset in exist_asset_list:
                raise ValidationError(_('The asset "%s" already exists in "%s" asset category, please change the asset!'%((line.asset_category_id.name), (line.asset_id.name), (line.operation_two_id.name))))
            exist_asset_list.append(asset)

class MrpBom(models.Model):
    _inherit = 'mrp.bom.line'
	
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True, domain="[('company_id','=',parent.company_id)]")

class MrpBomLabour(models.Model):
    _name = 'mrp.bom.labour'
    _check_company_auto = True
	
    sequence = fields.Integer(string="Sequence", default=0)
    bom_id = fields.Many2one('mrp.bom', string="BOM")
    operation_two_ids = fields.Many2many('mrp.bom.operation', related='bom_id.operation_two_ids')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True, domain="[('company_id','=',parent.company_id)]")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one( string='Company', readonly=True)
    quantity = fields.Float(string="Quantity", readonly=True)
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation', required=True, domain="[('id', 'in', operation_two_ids)]")
    cost = fields.Float(string="Cost", readonly=True)

    def domain_uom_id(self):
        wtime = self.env.ref('uom.uom_categ_wtime')
        return [('category_id', '=', wtime.id)]

    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure", domain=domain_uom_id)
    contractors = fields.Integer('Contractors', required=True, default= 1)
    time = fields.Integer('Time', required=True, default= 1)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
        else:
            self.uom_id = False

    @api.onchange('contractors', 'time',)
    def onchange_quantity(self):
        for line in self:
            quantity = (line.contractors * line.time)
            line.quantity = quantity

    @api.onchange('contractors', 'time')
    def _check_not_zero(self):
        for line in self:
            if line.contractors <= 0:
                raise ValidationError("The Contractors cannot be 0.")
            if line.time <= 0:
                raise ValidationError("The Time cannot be 0.")

class MrpBomoverhead(models.Model):
    _name = 'mrp.bom.overhead'
    _check_company_auto = True
	
    sequence = fields.Integer(string="Sequence", default=0)
    bom_id = fields.Many2one('mrp.bom', string="BOM")
    operation_two_ids = fields.Many2many('mrp.bom.operation', related='bom_id.operation_two_ids')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True, domain="[('company_id','=',parent.company_id)]")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(string='Company', readonly=True)
    quantity = fields.Float(string="Quantity", default= 1)
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure")
    overhead_catagory = fields.Selection([
        ('product', 'Product'),
        ('petty cash', 'Petty Cash'),
        ('cash advance', 'Cash Advance'),
        ('fuel', 'Fuel'),
    ], string='Overhead Catagory', required=False)
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation', required=True, domain="[('id', 'in', operation_two_ids)]")
    cost = fields.Float(string="Cost", readonly=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
        else:
            self.uom_id = False

    @api.onchange('quantity')
    def onchange_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('In overhead, the Product "%s" quantity should be greater than 0.'%((line.product_id.name))))

class MrpBomEquipment(models.Model):
    _name = 'mrp.bom.equipment'
    _check_company_auto = True

    sequence = fields.Integer(string="Sequence", default=0)
    bom_id = fields.Many2one('mrp.bom', string="BOM")
    operation_two_ids = fields.Many2many('mrp.bom.operation', related='bom_id.operation_two_ids')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True, domain="[('company_id','=',parent.company_id)]")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(string='Company', readonly=True)
    description = fields.Text(string="Description", required=True)
    quantity = fields.Float(string="Quantity", default= 1)
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure")
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation', required=True, domain="[('id', 'in', operation_two_ids)]")
    cost = fields.Float(string="Cost", readonly=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
        else:
            self.uom_id = False

    @api.onchange('quantity')
    def onchange_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('In equipment, the Product "%s" quantity should be greater than 0.'%((line.product_id.name))))

class MrpBomAsset(models.Model):
    _name = 'mrp.bom.asset'
    _check_company_auto = True

    sequence = fields.Integer(string="Sequence", default=0)
    bom_id = fields.Many2one('mrp.bom', string="BOM")
    operation_two_ids = fields.Many2many('mrp.bom.operation', related='bom_id.operation_two_ids')
    company_id = fields.Many2one(string='Company', readonly=True)
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category', required=True)
    asset_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    description = fields.Text(string="Description")
    quantity = fields.Float('Quantity', default=1)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation', required=True, domain="[('id', 'in', operation_two_ids)]")
    cost = fields.Float(string="Cost", readonly=True)

    @api.onchange('quantity')
    def onchange_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('In internal asset, the Product "%s" quantity should be greater than 0.'%((line.asset_id.name))))