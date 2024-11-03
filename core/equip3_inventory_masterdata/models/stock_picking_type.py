from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_transit = fields.Boolean(string="Transit Operation")
