from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    transfered_good_qty = fields.Float()
