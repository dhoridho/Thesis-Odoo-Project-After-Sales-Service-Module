from odoo import api, fields, models, _


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    sale_order_type = fields.Selection(
        [
            ("order", "Sale Order"),
            ("service", "Sale Order Service"),
        ],
        string="Sale Order Type",
    )
