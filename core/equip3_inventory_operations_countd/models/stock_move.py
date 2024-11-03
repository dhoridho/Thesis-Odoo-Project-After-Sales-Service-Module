from odoo import _, api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    description = fields.Char(
        related='product_id.display_name', string="Description")
