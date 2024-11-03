from odoo import models, fields


class CropActivityType(models.Model):
    _name = 'crop.activity.type'
    _description = 'Activity Type'

    name = fields.Char(required=True)
    value = fields.Char(required=True)
    category_ids = fields.Many2many('crop.activity.category', string='Activity Categories')

    _sql_constraints = [
        ('activity_type_value_unique', 'unique(value)', 'The value has been set for another category!')
    ]