from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class InternalTransfer(models.Model):
    _inherit = 'internal.transfer'

    # technical fields
    is_mrp_transfer_request = fields.Boolean()
    is_mrp_transfer_back = fields.Boolean()
    is_mrp_transfer_good = fields.Boolean()

    def action_confirm(self):
        res = super(InternalTransfer, self).action_confirm()
        for transfer in self.filtered(lambda o: o.is_mrp_transfer_good):
            for line in transfer.product_line_ids:
                product = line.product_id
                qty_to_take = line.uom._compute_quantity(line.qty, product.uom_id)

                for production in line.production_ids:
                    finished_moves = production.move_finished_only_ids.filtered(lambda o: o.product_id == product and o.state == 'done')

                    for move in finished_moves:
                        move_qty = move.product_uom._compute_quantity(max(0.0, move.quantity_done - move.transfered_good_qty), move.product_id.uom_id)
                        qty_taken = min(move_qty, qty_to_take)
                        move.transfered_good_qty += product.uom_id._compute_quantity(qty_taken, move.product_uom)
                        qty_to_take -= qty_taken
                        if qty_to_take <= 0.0:
                            break

                if qty_to_take > 0.0:
                    raise ValidationError(_("There's not enough Production Order quantity left!"))
        return res

class InternalTransferLine(models.Model):
    _inherit = 'internal.transfer.line'

    production_ids = fields.Many2many('mrp.production', string='Production Order')

    @api.onchange('product_id', 'qty', 'uom')
    def _set_production_ids(self):
        parent = self.product_line
        product = self.product_id
        uom = self.uom

        if not product or not uom or not parent.is_mrp_transfer_good:
            return
        
        qty_to_take = uom._compute_quantity(self.qty, product.uom_id)
        mrp_plan = self.env['mrp.plan'].search([('plan_id', '=', parent.source_document)])

        orders = self.env['mrp.production']
        if mrp_plan:
            for order in mrp_plan.mrp_order_ids:
                finished_moves = order.move_finished_only_ids.filtered(lambda o: o.product_id == product and o.state == 'done')

                for move in finished_moves:
                    move_qty = move.product_uom._compute_quantity(max(0.0, move.quantity_done - move.transfered_good_qty), move.product_id.uom_id)
                    qty_taken = min(move_qty, qty_to_take)
                    if qty_taken > 0.0:
                        orders |= order
                    qty_to_take -= qty_taken
                    if qty_to_take <= 0.0:
                        break
                
        elif qty_to_take > 0.0:
            orders = self.env['mrp.production'].search([('name', '=', parent.source_document)])

        self.production_ids = [(6, 0, orders.ids)]
