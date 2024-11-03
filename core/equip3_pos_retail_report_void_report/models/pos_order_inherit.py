from odoo import _, api, fields, models


class PosOrderInherit(models.Model):
    _inherit = 'pos.order'

    product_cancel_id = fields.Many2one("product.cancel", string="Product Cancel")
