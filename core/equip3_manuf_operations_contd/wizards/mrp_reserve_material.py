from odoo import models


class MrpReserveMaterial(models.TransientModel):
    _inherit = 'mrp.reserve.material'
    
    def action_confirm(self):
        result = super(MrpReserveMaterial, self).action_confirm()
        for line in self.line_ids:
            move = line.move_id
            move.dedicated_qty = move.product_uom._compute_quantity(line.reserved_uom_qty + line.to_reserve_uom_qty, move.product_id.uom_id)
        return result
