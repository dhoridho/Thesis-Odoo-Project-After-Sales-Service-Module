from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.mrp.models.stock_move import StockMove as MrpStockMove


class StockMove(models.Model):
    _inherit = 'stock.move'

    mrp_consumption_subcon_id = fields.Many2one('mrp.consumption', string='MPR Subcontracting')
    subcon_picking_id = fields.Many2one('stock.picking', string='Subcontracting Picking', copy=False)
    subcon_is_finished_good = fields.Boolean()
    requisition_line_id = fields.Many2one('purchase.requisition.line', string='Requisition Line')
    subcon_quantity_done = fields.Float(digits='Product Unit of Measure')
    subcon_move_id = fields.Many2one('stock.move', string='Subcontracting Move')

    """ 
    OPTIMIZATION
    functions bellow is not relevan anymore.
    """
    def _compute_show_subcontracting_details_visible(self):
        self.show_subcontracting_details_visible = False

    def _make_subcon_unlink(self):
        def unlink(self):
            # Avoid deleting move related to active MO
            for move in self:
                if move.production_id and move.production_id.state not in ('draft', 'cancel') and not move.production_id.is_subcontracted:
                    raise UserError(_('Please cancel the Manufacture Order first.'))
            return super(MrpStockMove, self).unlink()
        return unlink

    def _register_hook(self):
        MrpStockMove._patch_method('unlink', self._make_subcon_unlink())    
        return super(StockMove, self)._register_hook()

    def _prepare_common_svl_vals(self):
        values = super(StockMove, self)._prepare_common_svl_vals()
        if self.subcon_move_id and self.raw_material_production_id and values.get('move_internal_type') != 'out':
            values.update({
                'type': False,
                'mrp_plan_id': False,
                'mrp_production_id': False,
                'mrp_workorder_id': False,
                'mrp_consumption_id': False
            })
        return values
