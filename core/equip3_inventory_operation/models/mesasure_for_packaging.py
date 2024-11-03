from odoo import fields, models


class MeasureForPackaging(models.Model):
    _inherit = "measure.for.packaging"

    measure = fields.Selection([
        ('volume', 'Volume'),
        ('weight', 'Weight'),
    ], required=True)
