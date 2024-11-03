from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    kiosk_qty = fields.Float('Kiosk Quantity', digits='Product Unit of Measure', readonly=True)
