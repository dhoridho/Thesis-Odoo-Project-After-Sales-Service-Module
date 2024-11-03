from odoo import models, fields


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    mining_type = fields.Selection(
        selection=[
            ('material', 'Material'),
            ('finished', 'Finished Goods')
        ],
        string='Mining Type',
        default=False
    )

    mining_production_record_id = fields.Many2one('mining.production.record', string='Mining Production Record')
    mining_production_order_id = fields.Many2one('mining.daily.production.record', string='Mining Production Order')
    mining_input_id = fields.Many2one('mining.production.record.line.input', string='Mining Input')
    mining_output_id = fields.Many2one('mining.production.record.line.output', string='Mining Output')
