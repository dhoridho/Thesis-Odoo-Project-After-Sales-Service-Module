from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = "product.product"
    _order = "create_date desc"


class LibraryCard(models.Model):
    _inherit = "library.card"
    _order = "create_date desc"
