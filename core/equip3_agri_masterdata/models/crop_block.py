from odoo import models, fields, api, _
from ast import literal_eval
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class AgricultureCropBlock(models.Model):
    _name = 'crop.block'
    _inherit = ['image.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Crop Block Management'

    name = fields.Char(string='Name', required=True, tracking=True)
    estate_id = fields.Many2one('crop.estate', string='Estate', required=True, tracking=True)
    size = fields.Float(string='Area', default=1.0, tracking=True)
    uom_id = fields.Many2one('uom.uom', string='UOM', required=True, tracking=True)
    uom_category_id = fields.Many2one('uom.category', related='uom_id.category_id')
    crop_ids = fields.One2many('agriculture.crop', 'block_id', string='Crops', readonly=True)
    division_id = fields.Many2one('agriculture.division', string='Division', domain="[('estate_id', '=', estate_id)]", tracking=True)
    location_id = fields.Many2one('stock.location', string='Location', required=True, tracking=True)
    type = fields.Selection(selection=[
        ('nursery', 'Nursery'),
        ('plantation', 'Plantation')
    ], tracking=True)
    use_type = fields.Selection(selection=[
        ('block', 'Block'),
        ('nursery_area', 'Nursery Area')
    ], default='block', string='Use Type')
    sub_ids = fields.One2many('crop.block.sub', 'block_id', string='Sub-Blocks')

    @api.constrains('sub_ids', 'sub_ids.size', 'sub_ids.uom_id', 'size', 'uom_id')
    def _check_sub_size(self):
        for record in self:
            uom_id = record.uom_id
            sub_size = 0.0
            for sub in record.sub_ids:
                sub_size += sub.uom_id._compute_quantity(sub.size, uom_id)
            
            if sub_size > record.size:
                raise ValidationError(_('Size of sub-blocks cannot be more than size of block itself!'))


class AgricultureCropBlockSub(models.Model):
    _name = 'crop.block.sub'
    _description = 'Sub-Block'

    block_id = fields.Many2one('crop.block', required=True, ondelete='cascade')
    name = fields.Char(required=True, string='Sub-block')
    size = fields.Float(digits='Product Unit of Measure', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    state = fields.Selection(selection=[
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], default='inactive', string='Status', required=True, readonly=True)

    @api.constrains('size')
    def _check_size(self):
        for record in self:
            if record.size <= 0.0:
                raise ValidationError(_('Size must be positive!'))

    def action_set_active(self):
        self.ensure_one()
        self.state = 'active'

    def action_set_inactive(self):
        self.ensure_one()
        self.state = 'inactive'
