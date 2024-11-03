from odoo import _, api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for picking in self:
            procurement_planning = picking.purchase_id.procurement_planning_id
            if procurement_planning:
                procurement_line_dict = {
                    line.product_id.id: line for line in procurement_planning.procurement_line
                }

                for move in picking.move_ids_without_package:
                    line = procurement_line_dict.get(move.product_id.id)
                    if line:
                        line.quantity_received += move.quantity_done

        return res
