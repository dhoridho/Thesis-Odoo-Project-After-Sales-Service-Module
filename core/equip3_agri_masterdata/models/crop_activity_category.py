from odoo import models, fields


class CropActivityCategory(models.Model):
    _name = 'crop.activity.category'
    _description = 'Activity Category'

    name = fields.Char(required=True)
    value = fields.Char(required=True)
    group_ids = fields.One2many('crop.activity.group', 'category_id', string='Activity Groups')

    _sql_constraints = [
        ('activity_category_value_unique', 'unique(value)', 'The value has been set for another category!')
    ]
