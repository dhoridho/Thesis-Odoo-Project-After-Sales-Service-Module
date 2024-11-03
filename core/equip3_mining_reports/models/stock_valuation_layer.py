from odoo import models, fields, api, _


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    mining_type = fields.Selection(selection_add=[('overhead', 'Overhead')])
