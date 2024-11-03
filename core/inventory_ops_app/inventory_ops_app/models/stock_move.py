# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from odoo.tools.float_utils import float_compare
from odoo.tools import float_is_zero, OrderedSet
from itertools import groupby
from operator import itemgetter
from odoo.exceptions import ValidationError, UserError
import math


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_assign(self):
        """ Reserve stock moves by creating their stock move lines. A stock move is
        considered reserved once the sum of `product_qty` for all its move lines is
        equal to its `product_qty`. If it is less, the stock move is considered
        partially available.
        """
        ctx = self._context or {}
        if not ctx.get('picking_reserve', False):
            return super()._action_assign()
        StockMove = self.env['stock.move']
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        # Read the `reserved_availability` field of the moves out of the loop to prevent unwanted
        # cache invalidation when actually reserving the move.
        reserved_availability = {move: move.reserved_availability for move in self}
        # roundings = {move: move.product_id.uom_id.rounding for move in self}
        move_line_vals_list = []
        data_list = ctx.get('picking_reserve', [])
        for move_dict in data_list:
            move = self.env['stock.move'].browse(move_dict['move_id'])
            rounding = move.product_id.uom_id.rounding
            missing_reserved_uom_quantity = move_dict['qty']
            missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity,
                                                                           move.product_id.uom_id,
                                                                           rounding_method='HALF-UP')
            if move._should_bypass_reservation():
                # create the move line(s) but do not impact quants
                if move.product_id.tracking == 'serial' and (
                        move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
                    for i in range(0, int(missing_reserved_quantity)):
                        move_line_vals_list.append(move._prepare_move_line_vals(quantity=1))
                else:
                    to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
                                                                       ml.location_id == move.location_id and
                                                                       ml.location_dest_id == move.location_dest_id and
                                                                       ml.picking_id == move.picking_id and
                                                                       not ml.lot_id and
                                                                       not ml.package_id and
                                                                       not ml.owner_id)
                    if to_update:
                        to_update[0].product_uom_qty += missing_reserved_uom_quantity
                    else:
                        move_line_vals_list.append(move._prepare_move_line_vals(quantity=missing_reserved_quantity))
                assigned_moves_ids.add(move.id)
            else:
                if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                    assigned_moves_ids.add(move.id)
                elif not move.move_orig_ids:
                    if move.procure_method == 'make_to_order':
                        continue
                    # If we don't need any quantity, consider the move assigned.
                    need = missing_reserved_quantity
                    if float_is_zero(need, precision_rounding=rounding):
                        assigned_moves_ids.add(move.id)
                        continue
                    # Reserve new quants and create move lines accordingly.
                    forced_package_id = move.package_level_id.package_id or None
                    if move.product_id.tracking == 'none':
                        available_quantity = move._get_available_quantity(move.location_id,
                                                                          package_id=forced_package_id)
                        if available_quantity <= 0:
                            continue
                        taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id,
                                                                        package_id=forced_package_id, strict=False)
                        if float_is_zero(taken_quantity, precision_rounding=rounding):
                            continue
                        if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
                            assigned_moves_ids.add(move.id)
                        else:
                            partially_available_moves_ids.add(move.id)
                    else:
                        for lot_dict in move_dict.get('scanned_data', []):
                            if lot_dict['qty'] > 0:
                                lot_id = self.env['stock.production.lot'].search(
                                    [('name', '=', lot_dict['lot_name']), ('product_id', '=', move.product_id.id)],
                                    limit=1)
                                if lot_id:
                                    available_quantity = move._get_available_quantity(move.location_id, lot_id=lot_id,
                                                                                      package_id=forced_package_id)
                                    if available_quantity <= 0:
                                        continue
                                    taken_quantity = move._update_reserved_quantity(lot_dict['qty'], available_quantity,
                                                                                    move.location_id, lot_id=lot_id,
                                                                                    package_id=forced_package_id,
                                                                                    strict=False)
                                    if float_is_zero(taken_quantity, precision_rounding=rounding):
                                        continue
                                    if float_compare(lot_dict['qty'], taken_quantity, precision_rounding=rounding) == 0:
                                        assigned_moves_ids.add(move.id)
                                    else:
                                        partially_available_moves_ids.add(move.id)
                else:
                    # Check what our parents brought and what our siblings took in order to
                    # determine what we can distribute.
                    # `qty_done` is in `ml.product_uom_id` and, as we will later increase
                    # the reserved quantity on the quants, convert it here in
                    # `product_id.uom_id` (the UOM of the quants is the UOM of the product).
                    move_lines_in = move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')
                    keys_in_groupby = ['location_dest_id', 'lot_id', 'result_package_id', 'owner_id']

                    def _keys_in_sorted(ml):
                        return (ml.location_dest_id.id, ml.lot_id.id, ml.result_package_id.id, ml.owner_id.id)

                    grouped_move_lines_in = {}
                    for k, g in groupby(sorted(move_lines_in, key=_keys_in_sorted), key=itemgetter(*keys_in_groupby)):
                        qty_done = 0
                        for ml in g:
                            qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
                        grouped_move_lines_in[k] = qty_done
                    move_lines_out_done = (move.move_orig_ids.mapped('move_dest_ids') - move) \
                        .filtered(lambda m: m.state in ['done']) \
                        .mapped('move_line_ids')
                    # As we defer the write on the stock.move's state at the end of the loop, there
                    # could be moves to consider in what our siblings already took.
                    moves_out_siblings = move.move_orig_ids.mapped('move_dest_ids') - move
                    moves_out_siblings_to_consider = moves_out_siblings & (
                                StockMove.browse(assigned_moves_ids) + StockMove.browse(partially_available_moves_ids))
                    reserved_moves_out_siblings = moves_out_siblings.filtered(
                        lambda m: m.state in ['partially_available', 'assigned'])
                    move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped(
                        'move_line_ids')
                    keys_out_groupby = ['location_id', 'lot_id', 'package_id', 'owner_id']

                    def _keys_out_sorted(ml):
                        return (ml.location_id.id, ml.lot_id.id, ml.package_id.id, ml.owner_id.id)

                    grouped_move_lines_out = {}
                    for k, g in groupby(sorted(move_lines_out_done, key=_keys_out_sorted),
                                        key=itemgetter(*keys_out_groupby)):
                        qty_done = 0
                        for ml in g:
                            qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
                        grouped_move_lines_out[k] = qty_done
                    for k, g in groupby(sorted(move_lines_out_reserved, key=_keys_out_sorted),
                                        key=itemgetter(*keys_out_groupby)):
                        grouped_move_lines_out[k] = sum(
                            self.env['stock.move.line'].concat(*list(g)).mapped('product_qty'))
                    available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key
                                            in grouped_move_lines_in.keys()}
                    # pop key if the quantity available amount to 0
                    rounding = move.product_id.uom_id.rounding
                    available_move_lines = dict((k, v) for k, v in available_move_lines.items() if
                                                float_compare(v, 0, precision_rounding=rounding) > 0)

                    if not available_move_lines:
                        continue
                    for move_line in move.move_line_ids.filtered(lambda m: m.product_qty):
                        if available_move_lines.get((move_line.location_id, move_line.lot_id,
                                                     move_line.result_package_id, move_line.owner_id)):
                            available_move_lines[(move_line.location_id, move_line.lot_id, move_line.result_package_id,
                                                  move_line.owner_id)] -= move_line.product_qty
                    for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                        need = move.product_qty - sum(move.move_line_ids.mapped('product_qty'))
                        # `quantity` is what is brought by chained done move lines. We double check
                        # here this quantity is available on the quants themselves. If not, this
                        # could be the result of an inventory adjustment that removed totally of
                        # partially `quantity`. When this happens, we chose to reserve the maximum
                        # still available. This situation could not happen on MTS move, because in
                        # this case `quantity` is directly the quantity on the quants themselves.
                        available_quantity = move._get_available_quantity(location_id, lot_id=lot_id,
                                                                          package_id=package_id, owner_id=owner_id,
                                                                          strict=True)
                        if float_is_zero(available_quantity, precision_rounding=rounding):
                            continue
                        taken_quantity = move._update_reserved_quantity(need, min(quantity, available_quantity),
                                                                        location_id, lot_id, package_id, owner_id)
                        if float_is_zero(taken_quantity, precision_rounding=rounding):
                            continue
                        if float_is_zero(need - taken_quantity, precision_rounding=rounding):
                            assigned_moves_ids.add(move.id)
                            break
                        partially_available_moves_ids.add(move.id)
            if move.product_id.tracking == 'serial':
                move.next_serial_count = move.product_uom_qty

        self.env['stock.move.line'].create(move_line_vals_list)
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
        self.mapped('picking_id')._check_entire_pack()

    def action_app_put_in_package(self, vals):
        error_message = 'success'
        try:
            self.write(vals)
            self.app_action_put_in_package()
            return error_message
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
            return error_message

    def app_action_put_in_package(self):
        Quant = self.env['stock.quant']
        box = 0
        qty_wrote = 0
        packages = []
        packaging_volume = 0
        packaging_weight = 0
        product_volume = 0
        product_weight = 0
        qty_done = 0
        estimated_in_volume = 0
        estimated_in_weight = 0
        for record in self:
            print(record.qty_per_lot)
            total_weight_packages = 0
            if record.quantity_done <= 0 and record.qty_in_pack <= 0:
                raise ValidationError(
                    "Please add 'Done' quantities to the picking to create a new pack.")
            if record.qty_in_pack <= 0:
                raise ValidationError(
                    "Quantity to Put in Package must have a value in it and not 0.")
            if record.product_id.length == 0 or record.product_id.width == 0 or record.product_id.height == 0 or record.product_id.weight == 0:
                raise ValidationError(
                    "Product length or width or height or weight cannot 0.")
            if record.package_type.maximum_length == 0 or record.package_type.maximum_width == 0 or record.package_type.maximum_height == 0 or record.package_type.max_weight == 0:
                raise ValidationError(
                    "Product length or width or height or weight cannot 0.")

            # product packaging
            measure_ids = self.env['product.packaging'].search(
                [('id', '=', record.package_type.id)])
            if measure_ids:
                for x in measure_ids.measure_ids:
                    if x.measure == "volume":
                        packaging_volume = int(
                            record.package_type.maximum_length * record.package_type.maximum_width * record.package_type.maximum_height)
                        # measure product
                        if record.product_id.length:
                            product_length = record.product_id.length
                        if record.product_id.width:
                            product_width = record.product_id.width
                        if record.product_id.height:
                            product_height = record.product_id.height
                            product_volume = record.product_id.length * \
                                record.product_id.width * record.product_id.height
                        estimated_in_volume = packaging_volume / product_volume
                        if estimated_in_volume < 1:
                            raise ValidationError(
                                "This packages volume is to small, then cannot pack the product")
                        if estimated_in_volume <= 0:
                            estimated_in_volume = 9999999

                    elif x.measure == 'weight':
                        packaging_weight = record.package_type.max_weight
                        # measure product
                        if record.product_id.weight:
                            product_weight = record.product_id.weight
                        estimated_in_weight = packaging_weight / product_weight
                        if estimated_in_weight < 1:
                            raise ValidationError(
                                "This packages weight is to small, then cannot pack the product")
                        if estimated_in_weight <= 0:
                            estimated_in_weight = 9999999

            if estimated_in_weight <= 0:
                estimated_in_weight = 9999999
            if estimated_in_volume <= 0:
                estimated_in_volume = 9999999

            if estimated_in_weight <= estimated_in_volume:
                amount_weight = product_weight * record.qty_in_pack
                phone_in_box = 0
                if amount_weight > packaging_weight:
                    for x in range(1, record.qty_in_pack + 1):
                        phone_in_box += product_weight
                        if phone_in_box > packaging_weight:
                            box += 1
                            phone_in_box = product_weight
                        x += 1
                    over_product = phone_in_box // product_weight
                    for x in range(1, record.qty_in_pack + 1):
                        qty_done += product_weight
                        if qty_done > packaging_weight:
                            qty_done = (
                                qty_done - product_weight) // product_weight
                            break
                        x += 1
                    if over_product == 0:
                        box = box + 1

                # elif (product_weight * record.qty_in_pack) < record.package_type.max_weight:
                else:
                    box = 1
                    over_product = 0
                    qty_done = record.qty_in_pack

                if record.product_id.product_tmpl_id.tracking != 'none':
                    if record.qty_per_lot <= 0:
                        lot_names = self._generate_lot_numbers(box + 1)
                    else:
                        lot_serialize = math.ceil(
                            record.qty_in_pack / record.qty_per_lot)
                        lot_names = self._generate_lot_numbers(lot_serialize)
                        lot_names = lot_names[0]

                if box:
                    number_integer_for_serialize = 0
                    qty_udah_ketulis = 0
                    for x in range(0, int(box)):
                        final_package_id = self.env['stock.quant.package'].create({'package_measure_selection': 'weight',
                                                                                   'packaging_id': record.package_type.id,
                                                                                   'location_id': record.location_dest_id.id,
                                                                                   'weight': qty_done,
                                                                                   'volume': qty_done * product_volume})

                        if record.product_id.product_tmpl_id.tracking != 'none':
                            if record.qty_per_lot <= 0:
                                record.move_line_nosuggest_ids = [(0, 0, {
                                    'location_id': record.location_id.id,
                                    'location_dest_id': record.location_dest_id.id,
                                    'picking_id': record.picking_id.id,
                                    'result_package_id': final_package_id.id,
                                    'qty_done': qty_done,
                                    'product_uom_id': record.product_id.uom_id.id,
                                    'product_id': record.product_id.id,
                                    'lot_name': lot_names[x]
                                })]
                            else:
                                # assign
                                if x == 0:
                                    lot_batch = self._generate_lot_numbers(1)
                                qty_wrote += qty_done
                                if qty_wrote <= record.qty_per_lot:
                                    record.move_line_nosuggest_ids = [(0, 0, {
                                        'location_id': record.location_id.id,
                                        'location_dest_id': record.location_dest_id.id,
                                        'picking_id': record.picking_id.id,
                                        'result_package_id': final_package_id.id,
                                        'qty_done': qty_done,
                                        'product_uom_id': record.product_id.uom_id.id,
                                        'product_id': record.product_id.id,
                                        'lot_name': lot_names
                                    })]
                                    qty_udah_ketulis += qty_done
                                else:
                                    record.move_line_nosuggest_ids = [(0, 0, {
                                        'location_id': record.location_id.id,
                                        'location_dest_id': record.location_dest_id.id,
                                        'picking_id': record.picking_id.id,
                                        'result_package_id': final_package_id.id,
                                        'qty_done':  qty_wrote - record.qty_per_lot,
                                        'product_uom_id': record.product_id.uom_id.id,
                                        'product_id': record.product_id.id,
                                        'lot_name': lot_names
                                    })]
                                    # print('lot_batch',lot_batch)
                                    number_integer_for_serialize = number_integer_for_serialize + 1
                                    # print('number_integer_for_serialize',number_integer_for_serialize)
                                    # lot_batch = lot_batch[number_integer_for_serialize]
                                    # print(lot_batch)
                                    lot_names = self._generate_lot_numbers(
                                        int(lot_serialize))
                                    lot_names = lot_names[1]

                                    final_package_id = self.env['stock.quant.package'].create({'package_measure_selection': 'weight',
                                                                                               'packaging_id': record.package_type.id,
                                                                                               'location_id': record.location_dest_id.id,
                                                                                               'weight': qty_wrote - record.qty_per_lot,
                                                                                               'volume': qty_done * product_volume})

                                    record.move_line_nosuggest_ids = [(0, 0, {
                                        'location_id': record.location_id.id,
                                        'location_dest_id': record.location_dest_id.id,
                                        'picking_id': record.picking_id.id,
                                        'result_package_id': final_package_id.id,
                                        'qty_done': qty_wrote - record.qty_per_lot,
                                        'product_uom_id': record.product_id.uom_id.id,
                                        'product_id': record.product_id.id,
                                        'lot_name': lot_names
                                    })]
                                    qty_wrote = 0

                        else:
                            record.move_line_nosuggest_ids = [(0, 0, {
                                'location_id': record.location_id.id,
                                'location_dest_id': record.location_dest_id.id,
                                'picking_id': record.picking_id.id,
                                'result_package_id': final_package_id.id,
                                'qty_done': qty_done,
                                'product_uom_id': record.product_id.uom_id.id,
                                'product_id': record.product_id.id
                            })]

                if over_product > 0:
                    final_package_id = self.env['stock.quant.package'].create({'package_measure_selection': 'weight',
                                                                               'packaging_id': record.package_type.id,
                                                                               'location_id': record.location_dest_id.id,
                                                                               'weight': over_product,
                                                                               'volume': over_product * product_volume})

                    if record.product_id.product_tmpl_id.tracking != 'none':
                        if record.qty_per_lot <= 0:
                            record.move_line_nosuggest_ids = [(0, 0, {
                                'location_id': record.location_id.id,
                                'location_dest_id': record.location_dest_id.id,
                                'picking_id': record.picking_id.id,
                                'result_package_id': final_package_id.id,
                                'qty_done': over_product,
                                'product_uom_id': record.product_id.uom_id.id,
                                'product_id': record.product_id.id,
                                'lot_name': lot_names[-1]
                            })]

                        else:
                            record.move_line_nosuggest_ids = [(0, 0, {
                                'location_id': record.location_id.id,
                                'location_dest_id': record.location_dest_id.id,
                                'picking_id': record.picking_id.id,
                                'result_package_id': final_package_id.id,
                                'qty_done': over_product,
                                'product_uom_id': record.product_id.uom_id.id,
                                'product_id': record.product_id.id,
                                'lot_name': lot_names
                            })]

                    else:
                        record.move_line_nosuggest_ids = [(0, 0, {
                            'location_id': record.location_id.id,
                            'location_dest_id': record.location_dest_id.id,
                            'picking_id': record.picking_id.id,
                            'result_package_id': final_package_id.id,
                            'qty_done': over_product,
                            'product_uom_id': record.product_id.uom_id.id,
                            'product_id': record.product_id.id
                        })]

            if estimated_in_weight > estimated_in_volume:
                amount_volume = product_volume * record.qty_in_pack
                phone_in_box = 0
                if amount_volume > packaging_volume:
                    for x in range(1, record.qty_in_pack + 1):
                        phone_in_box += product_volume
                        if phone_in_box > packaging_volume:
                            box += 1
                            phone_in_box = product_volume
                        x += 1
                    over_product = phone_in_box // product_volume
                    for x in range(1, record.qty_in_pack + 1):
                        qty_done += product_volume
                        if qty_done > packaging_volume:
                            qty_done = (
                                qty_done - product_volume) // product_volume
                            break
                        x += 1
                    if over_product == 0:
                        box = box + 1

                else:
                    box = 1
                    over_product = 0
                    qty_done = record.qty_in_pack
                if box:
                    for x in range(0, int(box)):
                        final_package_id = self.env['stock.quant.package'].create({'package_measure_selection': 'volume',
                                                                                   'packaging_id': record.package_type.id,
                                                                                   'location_id': record.location_dest_id.id,
                                                                                   'volume': qty_done * product_volume})
                        if record.product_id.product_tmpl_id.tracking != 'none':
                            lot_names = self._generate_lot_numbers(box)
                            if lot_names:
                                lot_name = lot_names[x]
                                record.move_line_nosuggest_ids = [(0, 0, {
                                    'location_id': record.location_id.id,
                                    'location_dest_id': record.location_dest_id.id,
                                    'picking_id': record.picking_id.id,
                                    'result_package_id': final_package_id.id,
                                    'qty_done': qty_done,
                                    'product_uom_id': record.product_id.uom_id.id,
                                    'product_id': record.product_id.id,
                                    'lot_name': lot_name,
                                })]
                        else:
                            record.move_line_nosuggest_ids = [(0, 0, {
                                'location_id': record.location_id.id,
                                'location_dest_id': record.location_dest_id.id,
                                'picking_id': record.picking_id.id,
                                'result_package_id': final_package_id.id,
                                'qty_done': qty_done,
                                'product_uom_id': record.product_id.uom_id.id,
                                'product_id': record.product_id.id
                            })]

                if over_product > 0:
                    final_package_id = self.env['stock.quant.package'].create({'package_measure_selection': 'volume',
                                                                               'packaging_id': record.package_type.id,
                                                                               'location_id': record.location_dest_id.id,
                                                                               'volume': over_product * product_volume})
                    if record.product_id.product_tmpl_id.tracking != 'none':
                        lot_names = self._generate_lot_numbers(box+1)
                        if lot_names:
                            lot_name = lot_names[-1]
                            record.move_line_nosuggest_ids = [(0, 0, {
                                'location_id': record.location_id.id,
                                'location_dest_id': record.location_dest_id.id,
                                'picking_id': record.picking_id.id,
                                'result_package_id': final_package_id.id,
                                'qty_done': over_product,
                                'product_uom_id': record.product_id.uom_id.id,
                                'product_id': record.product_id.id,
                                'lot_name': lot_name,
                            })]
                    else:
                        record.move_line_nosuggest_ids = [(0, 0, {
                            'location_id': record.location_id.id,
                            'location_dest_id': record.location_dest_id.id,
                            'picking_id': record.picking_id.id,
                            'result_package_id': final_package_id.id,
                            'qty_done': over_product,
                            'product_uom_id': record.product_id.uom_id.id,
                            'product_id': record.product_id.id
                        })]

            record.picking_id._get_next_sequence_and_serial(move=record)

            for line in record.move_line_nosuggest_ids:
                if record.product_id.product_tmpl_id.tracking != 'none':
                    Quant.with_context({'move_id': record.id})._update_available_quantity(line.product_id,
                                                                                          line.location_dest_id,
                                                                                          line.qty_done, lot_id=line.lot_id,
                                                                                          package_id=line.result_package_id,
                                                                                          owner_id=line.owner_id)

                else:
                    Quant.with_context({'move_id': record.id})._update_available_quantity(line.product_id,
                                                                                          line.location_dest_id,
                                                                                          line.qty_done,
                                                                                          package_id=line.result_package_id,
                                                                                          owner_id=line.owner_id)

StockMove()