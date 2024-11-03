# -*- coding: utf-8 -*-

import copy
from itertools import groupby

from odoo import fields, api, models
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_picking_combo = fields.Boolean('Picking of Combo')
    pos_order_id = fields.Many2one('pos.order', 'POS order')
    pos_branch_id = fields.Many2one('res.branch', string='Branch', readonly=1, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])

    # def _pre_action_done_hook(self):
    #     res = super(StockPicking, self)._pre_action_done_hook()
    #     for p in self:
    #         if p.pos_order_id and p.is_picking_combo:
    #             return True
    #     return res


    def transfer_log_action(self):
        line_vals = []
        for rec in self:
            if rec.transfer_log_activity_ids:
                last_record_transfer_activity = rec.transfer_log_activity_ids[-1]

                before_state_value = dict(rec.fields_get(
                    allfields=['state'])['state']['selection'])[last_record_transfer_activity.state]
                after_state_value = dict(rec.fields_get(
                    allfields=['state'])['state']['selection'])[rec.state]
                action = before_state_value + ' To ' + after_state_value
                process_time = self._get_process_time()
                process_days = self._get_processed_days(process_time)
                line_vals.append((0, 0, {
                    'state': rec.state,
                    'action': action,
                    'timestamp': fields.datetime.now(),
                    'reference': rec.id,
                    'process_time': process_time,
                    'process_time_hours': rec._get_processed_hours(),
                    'process_days': process_days,
                    'user_id': self.env.user.id, }))
                rec.transfer_log_activity_ids = line_vals
                if rec.state in ('waiting', 'confirmed', 'assigned'):
                    for move in rec.move_ids_without_package:
                        move.scheduled_date = move.date
                else:
                    pass

        return True

    def _prepare_picking_vals(self, partner, picking_type, location_id, location_dest_id):
        context = self._context
        vals = super(StockPicking, self)._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
        pos_branch_id = False
        if 'pos_branch_id' in context:
            pos_branch_id = context['pos_branch_id']
            
        if not pos_branch_id:
            pos_branch_id = self.env['res.branch'].sudo().get_default_branch()
        vals['pos_branch_id'] = pos_branch_id

        return vals

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        # if len(lines) >= 1:
        #     order_picking_type = lines[0].order_id.picking_type_id
        #     if picking_type and order_picking_type and order_picking_type.id != picking_type.id:
        #         picking_type = order_picking_type
        pickings = super(StockPicking, self)._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type, partner=partner)
        return pickings

    def get_pos_stock_picking_sequence(self, picking_type, used_sequences):
        picking_sequence = picking_type.sequence_id.next_by_id()
        if picking_sequence in used_sequences:
            return self.get_pos_stock_picking_sequence(picking_type, used_sequences)

        picking = self.env['stock.picking'].search_read([('name','=', picking_sequence)], ['name'], limit=1)
        if picking:
            return self.get_pos_stock_picking_sequence(picking_type, used_sequences)
        return picking_sequence

    @api.model
    def create(self, vals):
        PosOrder = self.env['pos.order'].sudo()
        if vals.get('pos_order_id', None):
            order = PosOrder.browse(vals.get('pos_order_id'))
            if order.config_id and order.config_id.pos_branch_id: 
                vals.update({'pos_branch_id': order.config_id.pos_branch_id.id})

        if vals.get('pos_branch_id'):
            vals.update({ 'branch_id': vals['pos_branch_id'] })

        stock_picking_sequences = self._context.get('stock_picking_sequences') or []
        if self._context.get('create_picking_from_cron'):
            picking_type = self.env['stock.picking.type'].browse(vals.get('picking_type_id'))
            if picking_type and picking_type.sequence_id:
                picking_sequence = self.get_pos_stock_picking_sequence(picking_type, stock_picking_sequences)
                vals['name'] = picking_sequence
                
        return super(StockPicking, self).create(vals)

    def write(self, vals):
        PosOrder = self.env['pos.order'].sudo()
        if vals.get('pos_order_id', None):
            order = PosOrder.browse(vals.get('pos_order_id')) 
            if order.config_id and order.config_id.pos_branch_id:
                vals.update({'pos_branch_id': order.config_id.pos_branch_id.id})

        return super(StockPicking, self).write(vals)

    def _action_done(self):
        picking_obj = self.env['stock.picking']
        pickings = self
        if self.env.context.get('pos_order'):
            if self.env.context.get('pos_order').is_home_delivery or self.env.context.get('pos_order').is_pre_order :
                pickings = picking_obj
        return super(StockPicking, pickings)._action_done() 

    def get_key(self, val, my_dict):
        for key, value in my_dict.items():
            if val == value:
                return key

    def _prepare_stock_move_vals(self, first_line, order_lines):
        values = super(StockPicking, self)._prepare_stock_move_vals(first_line, order_lines)
        if first_line:
            values['pos_order_line_id'] = first_line.id

        #TODO: Convert product quantity from the pos order if uom is different
        list_qty = []
        for line in order_lines:
            qty = line.qty
            from_unit = line.product_uom_id
            to_unit = line.product_id.uom_id
            if from_unit and to_unit and (from_unit.id != to_unit.id):
                qty = from_unit._compute_quantity(qty, to_unit)
            list_qty += [qty]
        values['product_uom_qty'] = abs(sum(list_qty))

        return values

    def _prepare_product_bom_stock_move_vals(self, bom, default):
        # bom(pos.product.bom.line)
        self.ensure_one()
        product_uom_qty = default['product_uom_qty']
        values = copy.deepcopy(default)
        values.update({
            'name': bom.product_id.name,
            'product_id': bom.product_id.id,
            'product_uom': bom.product_id.uom_id.id,
            'product_uom_qty': abs(bom.product_qty * product_uom_qty),
            'quantity_done': abs(bom.product_qty * product_uom_qty),
        })
        return values

    def _prepare_all_values_stock_moves(self, lines, product, checking_uom):
        values = []
        first_line = []
        order_lines = []
        has_product_bundle = False
        get_uom_ids = checking_uom.get(product)
        all_list = list(get_uom_ids.values())
        all_list_is_true = all(map(lambda x: x == all_list[0], all_list)) # Check value if not None,False,0 then return True

        if all_list_is_true:
            product_id = self.env['product.product'].browse(product)
            order_lines = self.env['pos.order.line'].concat(*lines)
            first_line = order_lines[0]

            _process_type = False
            if product_id.is_pack:
                _process_type = 'product_pack' # Product Pack/ Product Bundle
            if not _process_type and (product_id.is_pos_bom and product_id.product_bom_id and product_id.product_bom_id.product_bom_line_ids):
                _process_type = 'pos_product_bom' # POS Product BOM

            if not _process_type:
                values += [self._prepare_stock_move_vals(first_line, order_lines)]

            if _process_type == 'product_pack':
                has_product_bundle = True
                bundle_id_before_change = product_id.product_tmpl_id
                
                for pack in product_id.bi_pack_ids:
                    pack_stock_move_vals = self._prepare_stock_move_vals(order_lines[0], order_lines) 
                    qty_bundle = pack_stock_move_vals['product_uom_qty']
                    pack_stock_move_vals.update({
                        'name': pack.product_id.name,
                        'product_id': pack.product_id.id,
                        'product_uom': pack.product_id.uom_id.id,
                        'product_uom_qty': pack.qty_uom * qty_bundle,
                        'initial_demand': pack.qty_uom * qty_bundle,
                        'qty_pack': pack.qty_uom, 
                        'is_pack': True,
                        'qty_bundle' : qty_bundle,
                        'id_bundle' : bundle_id_before_change, 
                        # 'analytic_account_group_ids': [(6,0,move.analytic_account_group_ids.ids)]
                    }) 
                    values += [pack_stock_move_vals]

            if _process_type == 'pos_product_bom':
                default_vals = self._prepare_stock_move_vals(first_line, order_lines) 
                for bom in product_id.product_bom_id.product_bom_line_ids:
                    values += [self._prepare_product_bom_stock_move_vals(bom, default_vals)]

        else:
            myset = list(set(all_list))
            for dt in myset:
                current_key = self.get_key(dt, get_uom_ids)
                order_lines = self.env['pos.order.line'].browse(current_key)
                values += [self._prepare_stock_move_vals(order_lines, order_lines)]
                first_line = order_lines

        return {
            'move_values': values, 
            'first_line': first_line,
            'order_lines': order_lines,
            'has_product_bundle': has_product_bundle,
        }

    # OVERRIDE
    def _create_move_from_pos_order_lines(self, lines):
        self.ensure_one()

        if lines:
            pos_order_id = lines[0].order_id
            self.write({'pos_order_id': pos_order_id.id}) 

        checking_uom_id = {}
        for line_by in lines:
            if line_by.product_id.id in checking_uom_id:
                temp_data = checking_uom_id.get(line_by.product_id.id)
                temp_data.update({line_by.id: line_by.uom_id.id})
                checking_uom_id.update({line_by.product_id.id: temp_data})
            else:
                checking_uom_id.update({line_by.product_id.id: {line_by.id: line_by.uom_id.id}})

        has_product_bundle = False
        lines_by_product = groupby(sorted(lines, key=lambda l: l.product_id.id), key=lambda l: l.product_id.id)
        for product, lines in lines_by_product:
            if product in checking_uom_id:
                all_values = self._prepare_all_values_stock_moves(lines, product, checking_uom_id)
                has_product_bundle = all_values['has_product_bundle']
                all_confirmed_moves = []
                for move_value in all_values['move_values']:
                    current_move = self.env['stock.move'].create(move_value)
                    confirmed_moves = current_move._action_confirm()
                    for dt in confirmed_moves:
                        all_confirmed_moves.append(dt.id)

                self._create_move_for_product_lots(all_confirmed_moves, all_values)

        # Update Sequence No.
        if has_product_bundle:
            bundle_groups = {}
            for move in self.move_ids_without_package:
                _key = move.id_bundle or '_1'
                bundle_groups[_key] = bundle_groups.get(_key, [])
                bundle_groups[_key].append(move)
                
            sequence = 1
            for k, bundle in bundle_groups.items():
                for move_id in bundle:
                    move_id.write({ 'move_line_sequence': sequence })
                    sequence += 1
                # return key

    def _create_move_for_product_lots(self, all_confirmed_moves, all_values):
        first_line = all_values['first_line']
        order_lines = all_values['order_lines']
        for move in self.env['stock.move'].browse(all_confirmed_moves):
            if first_line.product_id == move.product_id and first_line.product_id.tracking != 'none':
                if self.picking_type_id.use_existing_lots or self.picking_type_id.use_create_lots:
                    for line in order_lines:
                        sum_of_lots = 0
                        for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
                            if line.product_id.tracking == 'serial':
                                qty = 1
                            else:
                                qty = abs(line.qty)
                            ml_vals = move._prepare_move_line_vals()
                            ml_vals.update({'qty_done': qty})
                            if self.picking_type_id.use_existing_lots:
                                existing_lot = self.env['stock.production.lot'].search([
                                    ('company_id', '=', self.company_id.id),
                                    ('product_id', '=', line.product_id.id),
                                    ('name', '=', lot.lot_name)
                                ])
                                if not existing_lot and self.picking_type_id.use_create_lots:
                                    existing_lot = self.env['stock.production.lot'].create({
                                        'company_id': self.company_id.id,
                                        'product_id': line.product_id.id,
                                        'name': lot.lot_name,
                                    })
                                quant = existing_lot.quant_ids.filtered(
                                    lambda q: q.quantity > 0.0 and q.location_id.parent_path.startswith(
                                        move.location_id.parent_path))[-1:]
                                ml_vals.update({
                                    'lot_id': existing_lot.id,
                                    'location_id': quant.location_id.id or move.location_id.id
                                })
                            else:
                                ml_vals.update({
                                    'lot_name': lot.lot_name,
                                })
                            self.env['stock.move.line'].create(ml_vals)
                            sum_of_lots += qty
                        if abs(line.qty) != sum_of_lots:
                            difference_qty = abs(line.qty) - sum_of_lots
                            ml_vals = move._prepare_move_line_vals()
                            if line.product_id.tracking == 'serial':
                                ml_vals.update({'qty_done': 1})
                                for i in range(int(difference_qty)):
                                    self.env['stock.move.line'].create(ml_vals)
                            else:
                                ml_vals.update({'qty_done': difference_qty})
                                self.env['stock.move.line'].create(ml_vals)
                else:
                    move._action_assign()
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move_line.product_uom_qty
                    if float_compare(move.product_uom_qty, move.quantity_done,
                                     precision_rounding=move.product_uom.rounding) > 0:
                        remaining_qty = move.product_uom_qty - move.quantity_done
                        ml_vals = move._prepare_move_line_vals()
                        ml_vals.update({'qty_done': remaining_qty})
                        self.env['stock.move.line'].create(ml_vals)

            else:
                if self.user_has_groups('stock.group_tracking_owner'):
                    move._action_assign()
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move_line.product_uom_qty
                    if float_compare(move.product_uom_qty, move.quantity_done,
                                     precision_rounding=move.product_uom.rounding) > 0:
                        remaining_qty = move.product_uom_qty - move.quantity_done
                        ml_vals = move._prepare_move_line_vals()
                        ml_vals.update({'qty_done': remaining_qty})
                        self.env['stock.move.line'].create(ml_vals)
                move.quantity_done = move.product_uom_qty


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    pos_branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
    )