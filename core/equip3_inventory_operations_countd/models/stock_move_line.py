from odoo import _, api, fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    description = fields.Char(
        related='product_id.display_name', string="Description")
