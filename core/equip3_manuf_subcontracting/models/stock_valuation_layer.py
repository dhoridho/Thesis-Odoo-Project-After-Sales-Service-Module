from odoo import models, fields


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    type = fields.Selection(selection_add=[('subcon', 'Subcontracting'), ('mca_subcontracting', 'Actualization - Subcontracting')])