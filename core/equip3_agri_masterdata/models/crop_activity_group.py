from odoo import models, fields


class AgricultureCropActivityGroup(models.Model):
    _name = 'crop.activity.group'
    _description = 'Crop Activity Group'

    name = fields.Char(required=True, copy=False)
    category_id = fields.Many2one('crop.activity.category', string='Activity Category', required=True)
