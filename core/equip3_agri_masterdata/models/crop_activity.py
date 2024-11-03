from odoo import models, fields, api


class AgricultureCropActivity(models.Model):
    _name = 'crop.activity'
    _description = 'Crop Activity Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Activity', required=True, tracking=True)
    material_ids = fields.One2many('crop.activity.material', 'activity_id', string='Materials')
    crop_ids = fields.One2many('crop.activity.crop', 'activity_id', string='Crops')
    harvest_ids = fields.One2many('crop.activity.harvest', 'activity_id', string='Harvest')

    group_id = fields.Many2one('crop.activity.group', string='Activity Group', required=True, tracking=True)
    category_id = fields.Many2one('crop.activity.category', string='Activity Category', required=True, tracking=True, domain="[('id', 'in', allowed_category_ids)]")
    allowed_category_ids = fields.Many2many('crop.activity.category', compute='_compute_allowed_categories')
    category_type = fields.Char(related='category_id.value')

    type_id = fields.Many2one('crop.activity.type', string='Activity Type', required=True, domain="[('category_ids', 'in', [category_id])]", tracking=True)
    activity_type = fields.Char(related='type_id.value')

    product_id = fields.Many2one('product.product', string='Product', tracking=True)

    harvest_type_id = fields.Many2one('crop.activity.harvest.type', string='Harvest Type')
    harvest_type = fields.Char(related='harvest_type_id.value')

    @api.onchange('group_id')
    def _onchange_group_id(self):
        self.category_id = self.group_id and self.group_id.category_id or False

    @api.depends('group_id')
    def _compute_allowed_categories(self):
        categories = self.env['crop.activity.category'].search([])
        for record in self:
            allowed_category_ids = categories.filtered(lambda o: record.group_id in o.group_ids).ids
            record.allowed_category_ids = [(6, 0, allowed_category_ids)]


class AgricultureCropActivityMaterial(models.Model):
    _name = 'crop.activity.material'
    _description = 'Crop Activity Material'
    _rec_name = 'product_id'

    activity_id = fields.Many2one('crop.activity', string='Activity', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Material', required=True)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id')

    standard_area = fields.Float(string='Standard Area', digits='Product Unit of Measure', default=1.0)
    area_uom_id = fields.Many2one('uom.uom', string='Area Unit of Measure', required=True, default=lambda self: self.env.company.crop_default_uom_id)


class AgricultureCropActivityCrop(models.Model):
    _name = 'crop.activity.crop'
    _description = 'Crop Activity Crop'
    _rec_name = 'product_id'

    activity_id = fields.Many2one('crop.activity', string='Activity', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Crop', required=True, domain="[('is_agriculture_product', '=', True)]")
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Meaure', default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Product UoM', required=True)
    area = fields.Float(string='Standard Area', digits='Product Unit of Measure', default=1000.0)
    area_uom_id = fields.Many2one('uom.uom', string='Area UoM', required=True, default=lambda self: self.env.company.crop_default_uom_id)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id


class AgricultureCropActivityHarvest(models.Model):
    _name = 'crop.activity.harvest'
    _description = 'Crop Activity Harvest'
    _rec_name = 'product_id'

    activity_id = fields.Many2one('crop.activity', string='Activity', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Produce', required=True, domain="[('is_agriculture_product', '=', True)]")
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Meaure', default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Product UoM', required=True)
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id


class AgricultureCropActivityHarvestType(models.Model):
    _name = 'crop.activity.harvest.type'
    _description = 'Crop Activity Harvest Type'

    name = fields.Char(required=True)
    value = fields.Char(required=True)

    _sql_constraints = [
        ('activity_harvest_tyep_value_unique', 'unique(value)', 'The value has been set for another harvest type!')
    ]
