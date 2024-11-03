from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    mining_production_record_id = fields.Many2one('mining.production.record', string='Mining Production Record')
    mining_production_order_id = fields.Many2one('mining.daily.production.record', string='Mining Production Order')
    mining_input_id = fields.Many2one('mining.production.record.line.input', string='Mining Input')
    mining_output_id = fields.Many2one('mining.production.record.line.output', string='Mining Output')

    def _prepare_common_svl_vals(self):
        vals = super(StockMove, self)._prepare_common_svl_vals()
        if self.mining_production_record_id:
            vals['mining_production_record_id'] = self.mining_production_record_id.id
        if self.mining_production_order_id:
            vals['mining_production_order_id'] = self.mining_production_order_id.id
        if self.mining_input_id:
            vals['mining_input_id'] = self.mining_input_id.id
        if self.mining_output_id:
            vals['mining_output_id'] = self.mining_output_id.id
        
        if self.mining_production_record_id or self.mining_production_order_id:
            operation_type = (self.mining_production_record_id or self.mining_production_order_id).operation_type
            mining_type = 'finished'
            if operation_type == 'processing' and self.location_dest_id.id == self.product_id.with_company(self.company_id).property_stock_production.id:
                mining_type = 'material'
            vals['mining_type'] = mining_type
        return vals
