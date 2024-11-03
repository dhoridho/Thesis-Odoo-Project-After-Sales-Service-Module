from odoo import models, fields, api, _


class MrpUnbuild(models.Model):
    _inherit = 'mrp.unbuild'

    def _prepare_move_vals(self, product, qty, uom, location, location_dest, warehouse, **kwargs):
        res = super(MrpUnbuild, self)._prepare_move_vals(product, qty, uom, location, location_dest, warehouse, **kwargs)
        move = self.env['stock.move'].browse(kwargs.get('move_id', False))
        if move.raw_material_production_id:
            move_svls = move.stock_valuation_layer_ids
            res['price_unit'] = abs(sum(move_svls.mapped('value')) / sum(move_svls.mapped('quantity')))
        return res
