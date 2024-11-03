from odoo import models, fields


class AgricultureCrop(models.Model):
    _name = 'agriculture.crop'
    _inherit = ['image.mixin']
    _description = 'Crop Management'
    _rec_name = 'crop'

    crop = fields.Many2one('product.product', string='Crop', required=True, domain="[('is_agriculture_product', '=', True)]")
    block_id = fields.Many2one('crop.block', string='Block', readonly=True)
    sub_block_id = fields.Many2one('crop.block.sub', string='Sub-block', readonly=True)
    crop_count = fields.Float(string='Crop Count', default=1.0)
    crop_date = fields.Date(string='Crop Date', required=1)
    crop_phase = fields.Many2one('crop.phase', string='Crop Phase')
    crop_age = fields.Char(string='Crop Age', related='crop_phase.crop_age_str')
    uom_id = fields.Many2one('uom.uom', string='UOM')

    origin = fields.Char(readonly=True)
