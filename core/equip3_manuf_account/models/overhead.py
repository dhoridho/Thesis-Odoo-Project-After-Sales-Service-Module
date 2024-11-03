from odoo import models, fields, api, _


class OverheadTime(models.Model):
    _inherit = 'overhead.time'

    cost_hr = fields.Float(string="Cost/Hour", default=0.0)


class OverheadMaterial(models.Model):
    _inherit = 'overhead.material'

    product_price = fields.Float(string="Product Cost Price", related='product.standard_price')
