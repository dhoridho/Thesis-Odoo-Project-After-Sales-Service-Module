from odoo import models, _

class MrpStockReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    def _make_dict_move(self, level, parent_id, move_line, unfoldable=False):
        res_model, res_id, ref = self._get_reference(move_line)
        dummy, is_used = self._get_linked_move_lines(move_line)
        data = [{
            'level': level,
            'unfoldable': unfoldable,
            'date': move_line.move_id.date,
            'parent_id': parent_id,
            'is_used': bool(is_used),
            'usage': self._get_usage(move_line),
            'model_id': move_line.id,
            'model': 'stock.move.line',
            'product_id': move_line.product_id.display_name,
            'product_qty_uom': "%s %s" % (self._quantity_to_str(move_line.product_uom_id, move_line.product_id.uom_id, move_line.qty_done), move_line.product_id.uom_id.name),
            'lot_name': move_line.lot_id.name,
            'lot_id': move_line.lot_id.id,
            'location_source': move_line.location_id.name,
            'location_destination': move_line.location_dest_id.complete_name,
            'reference_id': ref,
            'res_id': res_id,
            'res_model': res_model}]
        return data