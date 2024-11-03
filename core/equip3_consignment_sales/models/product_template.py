from odoo import _, api, fields, models


class ProductTemplateIn(models.Model):
    _inherit = 'product.template'

    is_consignment_sales = fields.Boolean("Is Consignment Sales Product")