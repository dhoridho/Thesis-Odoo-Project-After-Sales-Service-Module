from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.onchange('partner_id')
    def get_partner_location(self):
        context = dict(self.env.context)
        # print('con_out', context.get('picking_type_code'))
        if context.get('picking_type_code') == 'incoming':
            self.location_dest_id = self.partner_id.preferred_location.id
        if context.get('picking_type_code') == 'outgoing':
            self.location_id = self.partner_id.preferred_location.id

    def action_put_in_pack(self):
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            picking_move_lines = self.move_line_ids
            if (
                not self.picking_type_id.show_reserved
                and not self.immediate_transfer
                and not self.env.context.get('barcode_view')
            ):
                picking_move_lines = self.move_line_nosuggest_ids

            move_line_ids = picking_move_lines.filtered(lambda ml:
                float_compare(ml.qty_done, 0.0, precision_rounding=ml.product_uom_id.rounding) > 0
                and not ml.result_package_id
            )
            if not move_line_ids:
                move_line_ids = picking_move_lines.filtered(lambda ml: float_compare(ml.product_uom_qty, 0.0,
                                     precision_rounding=ml.product_uom_id.rounding) > 0 and float_compare(ml.qty_done, 0.0,
                                     precision_rounding=ml.product_uom_id.rounding) == 0)
            if move_line_ids:
                res = self._pre_put_in_pack_hook(move_line_ids)
                if not res:
                    res = self._put_in_pack(move_line_ids)
                    if res:
                        package_move_line_id = picking_move_lines.filtered(lambda ml: ml.result_package_id and ml.result_package_id.id==res.id)
                        if package_move_line_id and package_move_line_id.location_id and package_move_line_id.product_id:
                            package_location_id = package_move_line_id.location_id
                            package_product_id = package_move_line_id.product_id
                            search_no_pack_quant = self.env['stock.quant'].sudo().search([('location_id', '=', package_location_id.id), ('product_id', '=', package_product_id.id), ('package_id', '=', False)], limit=1)
                            if search_no_pack_quant:
                                current_available_qty = search_no_pack_quant.available_quantity
                                new_available_qty = current_available_qty - package_move_line_id.qty_done
                                search_no_pack_quant.sudo().write({
                                    'available_quantity': new_available_qty
                                })

                return res
            else:
                raise UserError(_("Please add 'Done' quantities to the picking to create a new pack."))
