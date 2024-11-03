
from odoo import api, fields, models, _


class MaterialRequestShowStock(models.TransientModel):
    _name = "material.request.show.stock"
    _description = 'Material Request Show Stock'

    stock_quant_line_ids = fields.One2many('material.request.line.show.stock', 'stock_quant_id',  string="Stock Quant")

class MaterialRequestLineShowStock(models.TransientModel):
    _name = "material.request.line.show.stock"
    _description = 'Material Request Line Show Stock'

    stock_quant_id = fields.Many2one('material.request.show.stock', string="Stock Quant")
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float(string="On Hand")
    available_quantity = fields.Float(string="Available Quantity")
    forecast_incoming = fields.Float(string="Forecast Incoming")
    forecast_outcoming = fields.Float(string="Forecast Outgoing")
    forecast_qty = fields.Float(string="Forecast Quantity")
    location_id = fields.Many2one('stock.location', string="Location")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
