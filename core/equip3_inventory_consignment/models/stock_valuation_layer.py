from odoo import models, fields, api, _

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    is_consignment = fields.Boolean('Is Consignment')
    consignment_id = fields.Many2one('consignment.agreement')


class StockValuationLayerLine(models.Model):
    _inherit = 'stock.valuation.layer.line'

    is_source_consignment = fields.Boolean(related='svl_source_id.is_consignment', string='Is Consignment Source')
    consignment_source_id = fields.Many2one(related='svl_source_id.consignment_id', string='Consignment Source')
