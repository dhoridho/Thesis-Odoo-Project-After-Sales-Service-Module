from odoo import _, api, fields, models
from collections import defaultdict
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.addons.stock.models.stock_rule import ProcurementException
import logging
from itertools import groupby

class StockMoveInherit(models.Model):
    _inherit = 'stock.move'

    # def _get_new_picking_values(self):
    #     res = super(StockMoveInherit,self)._get_new_picking_values()
    #     branch_id = self.mapped('branch_id') and self.mapped('branch_id')[0].id or False
    #     res.update({
    #         'branch_id':branch_id
    #     })
    #     return res

    def _get_new_picking_values(self):
        res = super(StockMoveInherit,self)._get_new_picking_values()
        location = self.location_id
        branch_id = self.branch_id.id
        picking_type = self.picking_type_id
        warehouse = picking_type.warehouse_id
        res.update({
            'branch_id':branch_id,
            'warehouse_id':location.warehouse_id.id,
        })
        if picking_type.code=='outgoing' and warehouse.default_delivery_location_id:
            res.update({
                'location_id': warehouse.default_delivery_location_id.id,
            })
        return res

    def _assign_picking(self):
        if 'from_action_confirm' in self.env.context:
            Picking = self.env['stock.picking']
            grouped_moves = groupby(sorted(self, key=lambda m: [f.id for f in m._key_assign_picking()]), key=lambda m: [m._key_assign_picking()])
            for group, moves in grouped_moves:
                moves = self.env['stock.move'].concat(*list(moves))
                new_picking = False
                # Could pass the arguments contained in group but they are the same
                # for each move that why moves[0] is acceptable
                picking = moves[0]._search_picking_for_assignation()
                if picking:
                    if any(picking.partner_id.id != m.partner_id.id or
                           picking.origin != m.origin for m in moves):
                        # If a picking is found, we'll append `move` to its move list and thus its
                        # `partner_id` and `ref` field will refer to multiple records. In this
                        # case, we chose to  wipe them.
                        picking.write({
                            'partner_id': False,
                            'origin': False,
                        })
                else:
                    new_picking = True
                    # picking = Picking.create(moves._get_new_picking_values())
                    move_value = moves._get_new_picking_values()
                    move_value['sale_id'] = self.group_id.sale_id.id
                    picking = Picking.query_insert_picking(move_value)
                    if move_value.get('carrier_id'):
                        picking.carrier_id = move_value.get('carrier_id')


            moves.write({'picking_id': picking.id, 'location_id': picking.location_id.id})
            moves._assign_picking_post_process(new=new_picking)
            return True
        else:
            res = super()._assign_picking()
            return res