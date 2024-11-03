from odoo import models, fields, api, _
from odoo.osv import expression


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _production_prepare_account_move_vals(self):
        move_vals = super(StockValuationLayer, self)._production_prepare_account_move_vals()
        branch = self.env.branch
        if self.mca_id:
            branch = self.mca_id.branch_id
        move_vals = self.env['account.move']._query_complete_account_move_fields(move_vals, branch)
        return move_vals

    @api.model
    def _production_create_account_moves(self, vals_list):
        self.env['account.move']._query_create(vals_list)


class StockValuationLayerLine(models.Model):
    _inherit = 'stock.valuation.layer.line'

    svl_source_production_id = fields.Many2one('mrp.production', related='svl_source_id.mrp_production_id', string='Source Production Order')
