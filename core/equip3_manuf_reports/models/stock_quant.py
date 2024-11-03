from odoo import models, fields, _


class StockQuant(models.Model):
    _inherit = "stock.quant"

    length = fields.Float(string="Length", related="lot_id.length")
    height = fields.Float(string="Height", related="lot_id.height")
    width = fields.Float(string="Width", related="lot_id.width")
