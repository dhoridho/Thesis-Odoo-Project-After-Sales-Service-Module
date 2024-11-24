from odoo import fields, models


class MeasureForPackaging(models.Model):
    _name = "measure.for.packaging"
    _description = 'Measure for Packaging'
    _rec_name = 'measure'

    measure = fields.Selection([
        ('weight', 'Weight'),
        ('volume', 'Volume')
    ])
