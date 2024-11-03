# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_repr, float_round


class StockMove(models.Model):
    _inherit = 'stock.move'

    reserved_availability_stored = fields.Float('Quantity Reserved Stored', digits='Product Unit of Measure', readonly=True, help='Quantity that has already been reserved for this move')

    @api.depends('move_line_ids.product_qty')
    def _compute_reserved_availability(self):
        res = super()._compute_reserved_availability()
        for record in self:
            record.reserved_availability_stored = record.reserved_availability
        return res

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        if not self.env.context.get('process_from_app'):
            return super()._update_reserved_quantity(need, available_quantity, location_id, lot_id, package_id, owner_id, strict)
        """ Create or update move lines."""
        self.ensure_one()

        # To avoid validation issue
        available_quantity = need

        if not lot_id:
            lot_id = self.env['stock.production.lot']
        if not package_id:
            package_id = self.env['stock.quant.package']
        if not owner_id:
            owner_id = self.env['res.partner']

        taken_quantity = min(available_quantity, need)

        # `taken_quantity` is in the quants unit of measure. There's a possibility that the move's
        # unit of measure won't be respected if we blindly reserve this quantity, a common usecase
        # is if the move's unit of measure's rounding does not allow fractional reservation. We chose
        # to convert `taken_quantity` to the move's unit of measure with a down rounding method and
        # then get it back in the quants unit of measure with an half-up rounding_method. This
        # way, we'll never reserve more than allowed. We do not apply this logic if
        # `available_quantity` is brought by a chained move line. In this case, `_prepare_move_line_vals`
        # will take care of changing the UOM to the UOM of the product.
        if not strict and self.product_id.uom_id != self.product_uom:
            taken_quantity_move_uom = self.product_id.uom_id._compute_quantity(taken_quantity, self.product_uom, rounding_method='DOWN')
            taken_quantity = self.product_uom._compute_quantity(taken_quantity_move_uom, self.product_id.uom_id, rounding_method='HALF-UP')

        quants = []
        rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        if self.product_id.tracking == 'serial':
            if float_compare(taken_quantity, int(taken_quantity), precision_digits=rounding) != 0:
                taken_quantity = 0

        try:
            with self.env.cr.savepoint():
                if not float_is_zero(taken_quantity, precision_rounding=self.product_id.uom_id.rounding):
                    quants = self.env['stock.quant']._update_reserved_quantity(
                        self.product_id, location_id, taken_quantity, lot_id=lot_id,
                        package_id=package_id, owner_id=owner_id, strict=strict
                    )
        except UserError:
            taken_quantity = 0

        # Find a candidate move line to update or create a new one.
        for reserved_quant, quantity in quants:

            # To fix validation issue
            quantity = taken_quantity

            to_update = next((line for line in self.move_line_ids if line._reservation_is_updatable(quantity, reserved_quant)), False)
            if to_update:
                uom_quantity = self.product_id.uom_id._compute_quantity(quantity, to_update.product_uom_id, rounding_method='HALF-UP')
                uom_quantity = float_round(uom_quantity, precision_digits=rounding)
                uom_quantity_back_to_product_uom = to_update.product_uom_id._compute_quantity(uom_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
            if to_update and float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                to_update.with_context(bypass_reservation_update=True).product_uom_qty += uom_quantity
            else:
                if self.product_id.tracking == 'serial':
                    self.env['stock.move.line'].create([self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant) for i in range(int(quantity))])
                else:
                    self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))
        return taken_quantity


    # def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
    #     if self.env.context.get('process_from_app'):
    #         return need
    #     return super()._update_reserved_quantity(need, available_quantity, location_id, lot_id, package_id, owner_id, strict)

    def _get_available_quantity(self, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False):
        if self.env.context.get('process_from_app'):
            return 10000.0
        return super()._get_available_quantity(location_id, lot_id, package_id, owner_id, strict, allow_negative)

    def _should_bypass_reservation(self):
        if self.env.context.get('process_from_app'):
            return True
        return super()._should_bypass_reservation()

    # def _app_action_confirm(self, merge=True, merge_into=False):
    #     # move_create_proc = self.env['stock.move']
    #     # move_to_confirm = self.env['stock.move']
    #     # move_waiting = self.env['stock.move']
    #
    #     # to_assign = {}
    #     # for move in self:
    #     #     if move.state != 'draft':
    #     #         continue
    #         # if the move is preceeded, then it's waiting (if preceeding move is done, then action_assign has been called already and its state is already available)
    #         # if move.move_orig_ids:
    #         #     move_waiting |= move
    #         # else:
    #         #     if move.procure_method == 'make_to_order':
    #         #         move_create_proc |= move
    #         #     else:
    #         # move_to_confirm |= move
    #         # if move._should_be_assigned():
    #         #     key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
    #         #     if key not in to_assign:
    #         #         to_assign[key] = self.env['stock.move']
    #         #     to_assign[key] |= move
    #
    #     # create procurements for make to order moves
    #     # procurement_requests = []
    #     # for move in move_create_proc:
    #     #     values = move._prepare_procurement_values()
    #     #     origin = (move.group_id and move.group_id.name or (move.origin or move.picking_id.name or "/"))
    #     #     procurement_requests.append(self.env['procurement.group'].Procurement(
    #     #         move.product_id, move.product_uom_qty, move.product_uom,
    #     #         move.location_id, move.rule_id and move.rule_id.name or "/",
    #     #         origin, move.company_id, values))
    #     # self.env['procurement.group'].run(procurement_requests,
    #     #                                   raise_user_error=not self.env.context.get('from_orderpoint'))
    #
    #     self.write({'state': 'confirmed'})
    #     # (move_waiting | move_create_proc).write({'state': 'waiting'})
    #
    #     # assign picking in batch for all confirmed move that share the same details
    #     # for moves in to_assign.values():
    #     #     moves._assign_picking()
    #     # self._push_apply()
    #     # self._check_company()
    #     moves = self
    #     if merge:
    #         moves = self._merge_moves(merge_into=merge_into)
    #     # call `_action_assign` on every confirmed move which location_id bypasses the reservation
    #     # moves.filtered(lambda move: not move.picking_id.immediate_transfer and move._should_bypass_reservation() and move.state == 'confirmed')._action_assign()
    #     moves._action_assign()
    #     return moves

    def _app_action_confirm(self, merge=True, merge_into=False):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        :param: merge: According to this boolean, a newly confirmed move will be merged
        in another move of the same picking sharing its characteristics.
        """
        # move_create_proc = self.env['stock.move']
        move_to_confirm = self.env['stock.move']
        # move_waiting = self.env['stock.move']

        to_assign = {}
        for move in self:
            # if move.state != 'draft':
            #     continue
            # # if the move is preceeded, then it's waiting (if preceeding move is done, then action_assign has been called already and its state is already available)
            # if move.move_orig_ids:
            #     move_waiting |= move
            # else:
            #     if move.procure_method == 'make_to_order':
            #         move_create_proc |= move
            #     else:
            move_to_confirm |= move
            if move._should_be_assigned():
                key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
                if key not in to_assign:
                    to_assign[key] = self.env['stock.move']
                to_assign[key] |= move

        # create procurements for make to order moves
        procurement_requests = []
        # for move in move_create_proc:
        #     values = move._prepare_procurement_values()
        #     origin = (move.group_id and move.group_id.name or (move.origin or move.picking_id.name or "/"))
        #     procurement_requests.append(self.env['procurement.group'].Procurement(
        #         move.product_id, move.product_uom_qty, move.product_uom,
        #         move.location_id, move.rule_id and move.rule_id.name or "/",
        #         origin, move.company_id, values))
        # self.env['procurement.group'].run(procurement_requests, raise_user_error=not self.env.context.get('from_orderpoint'))

        move_to_confirm.write({'state': 'confirmed'})
        # (move_waiting | move_create_proc).write({'state': 'waiting'})

        # assign picking in batch for all confirmed move that share the same details
        for moves in to_assign.values():
            moves._assign_picking()
        # self._push_apply()
        # self._check_company()
        moves = self
        if merge:
            moves = self._merge_moves(merge_into=merge_into)
        # call `_action_assign` on every confirmed move which location_id bypasses the reservation
        moves.filtered(lambda move: not move.picking_id.immediate_transfer and move._should_bypass_reservation() and move.state == 'confirmed')._action_assign()
        return moves

    def _quantity_done_set(self):
        if self.env.context.get('process_from_app'):
            # quantity_done = self[0].quantity_done  # any call to create will invalidate `move.quantity_done`
            for move in self:
                if move.picking_id.picking_type_code != "incoming":
                    move_lines = move._get_move_lines()
                    if len(move_lines) > 1:
                        for line in move_lines:
                            line.qty_done = line.product_uom_qty
        return super(StockMove, self)._quantity_done_set()

    def _get_move_lines(self):
        """ This will return the move lines to consider when applying _quantity_done_compute on a stock.move.
        In some context, such as MRP, it is necessary to compute quantity_done on filtered sock.move.line."""
        self.ensure_one()
        if self.env.context.get('process_from_app'):
            return self.move_line_ids
        return super(StockMove, self)._get_move_lines()