# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo.tools import float_compare, float_is_zero


def _find(lines, line_id):
    for line in lines:
        if line['id'] == line_id:
            return line
    return False


class MrpConsumption(models.Model):
    _name = 'mrp.consumption'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Production Record'

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('mrp.consumption') or _('New')
        return super(MrpConsumption, self).create(vals)

    @api.depends(
    'move_finished_ids', 'move_finished_ids.product_id', 'move_finished_ids.quantity_done', 'finished_lot_ids', 'finished_lot_ids.product_id', 'finished_lot_ids.consumption_qty', 'rejected_lot_ids', 'rejected_lot_ids.product_id', 'rejected_lot_ids.consumption_qty',
    'byproduct_ids', 'byproduct_ids.product_id', 'byproduct_ids.quantity_done', 'byproduct_lot_ids', 'byproduct_lot_ids.product_id', 'byproduct_lot_ids.consumption_qty')
    def _compute_is_disable_generate(self):

        def is_generated(product_qty, lot_ids):
            return sum(lot_ids.mapped('consumption_qty')) >= product_qty

        for record in self:
            finished_product_ids = record.move_finished_ids.mapped('product_id').filtered(lambda p: p._is_auto_generate())
            finished_generated = all(
                is_generated(sum(record.move_finished_ids.filtered(lambda b: b.product_id == product).mapped('quantity_done')), 
                (record.finished_lot_ids | record.rejected_lot_ids).filtered(lambda b: b.product_id == product)) for product in finished_product_ids)

            byproduct_product_ids = record.byproduct_ids.mapped('product_id').filtered(lambda p: p._is_auto_generate())
            byproduct_generated = all(
                is_generated(sum(record.byproduct_ids.filtered(lambda b: b.product_id == product).mapped('quantity_done')), 
                record.byproduct_lot_ids.filtered(lambda b: b.product_id == product)) for product in byproduct_product_ids)
            
            record.is_disable_generate = finished_generated and byproduct_generated

    @api.depends('product_id')
    def _compute_is_autogenerate(self):
        for record in self:
            product_id = record.product_id
            record.is_autogenerate = product_id and product_id._is_auto_generate() or False

    @api.depends('finished_qty', 'rejected_qty')
    def _compute_product_qty(self):
        for record in self:
            record.product_qty = record.finished_qty + record.rejected_qty

    @api.depends('byproduct_ids', 'byproduct_ids.product_id', 'byproduct_ids.quantity_done', 'byproduct_lot_ids', 'byproduct_lot_ids.consumption_qty')
    def _compute_byproduct_products(self):
        for record in self:
            product_ids = record.byproduct_ids.mapped('product_id')
            record.show_byproduct_lot_tab = any(p.tracking in ('lot', 'serial') for p in product_ids)

            manual_product_ids = product_ids.filtered(lambda p: p._is_manual_generate())
            auto_product_ids = product_ids.filtered(lambda p: p._is_auto_generate())

            manual_no_repeat_product_ids = manual_product_ids.filtered(lambda p:
                sum(record.byproduct_ids.filtered(lambda b: b.product_id == p).mapped('quantity_done')) > \
                    sum(record.byproduct_lot_ids.filtered(lambda b: b.product_id == p).mapped('consumption_qty')))
            
            default_lot = {p.id: sum(record.byproduct_ids.filtered(lambda b: b.product_id == p).mapped('quantity_done')) - \
                sum(record.byproduct_lot_ids.filtered(lambda b: b.product_id == p).mapped('consumption_qty')) \
                    for p in manual_no_repeat_product_ids.filtered(lambda p: p.tracking == 'lot')}

            record.byproduct_manual_product_ids = [(6, 0, manual_no_repeat_product_ids.ids)]
            record.default_byproduct_lot_qty = json.dumps(default_lot)
            record.default_next_byproduct_product_id = manual_no_repeat_product_ids and manual_no_repeat_product_ids[0].id or False
            record.any_byproduct_is_autogenerate = len(auto_product_ids) > 0
            record.all_byproduct_is_autogenerate = len(manual_product_ids) == 0

    @api.depends(
        'move_finished_ids', 'move_finished_ids.product_id', 'move_finished_ids.mpr_finished_qty', 'move_finished_ids.mpr_rejected_qty', 
        'finished_lot_ids', 'finished_lot_ids.consumption_qty', 'rejected_lot_ids', 'rejected_lot_ids.consumption_qty', 'is_last_workorder')
    def _compute_finished_products(self):
        for record in self:
            product_ids = record.move_finished_ids.mapped('product_id')
            manual_product_ids = product_ids.filtered(lambda p: p._is_manual_generate())
            auto_product_ids = product_ids.filtered(lambda p: p._is_auto_generate())

            record.show_finished_lot_tab = record.is_last_workorder and any(p.tracking in ('lot', 'serial') for p in product_ids)
            record.any_finished_is_autogenerate = len(auto_product_ids) > 0
            record.all_finished_is_autogenerate = len(manual_product_ids) == 0

            for ftype in ['finished', 'rejected']:
                manual_no_repeat_product_ids = manual_product_ids.filtered(lambda p:
                    sum(record.move_finished_ids.filtered(lambda b: b.product_id == p).mapped('mpr_%s_qty' % ftype)) > \
                        sum(record['%s_lot_ids' % ftype].filtered(lambda b: b.product_id == p).mapped('consumption_qty')))
                
                default_lot = {p.id: sum(record.move_finished_ids.filtered(lambda b: b.product_id == p).mapped('mpr_%s_qty' % ftype)) - \
                    sum(record['%s_lot_ids' % ftype].filtered(lambda b: b.product_id == p).mapped('consumption_qty')) \
                        for p in manual_no_repeat_product_ids.filtered(lambda p: p.tracking == 'lot')}

                record['%s_manual_product_ids' % ftype] = [(6, 0, manual_no_repeat_product_ids.ids)]
                record['default_%s_lot_qty' % ftype] = json.dumps(default_lot)
                record['default_next_%s_product_id' % ftype] = manual_no_repeat_product_ids and manual_no_repeat_product_ids[0].id or False
    

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'), tracking=True)
    manufacturing_plan = fields.Many2one('mrp.plan', 'Production Plan', tracking=True)
    manufacturing_order_id = fields.Many2one('mrp.production', string='Production Order', tracking=True)
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order', tracking=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True, tracking=True)
    product_uom_id = fields.Many2one('uom.uom', readonly=True)

    finished_qty = fields.Float(
        string='Finished Product', digits='Product Unit of Measure', readonly=True,
        states={'draft': [('readonly', False)]}, tracking=True)
    rejected_qty = fields.Float(
        string='Rejected Product', digits='Product Unit of Measure', readonly=True,
        states={'draft': [('readonly', False)]}, tracking=True)
    product_qty = fields.Float(
        string='Product Quantity',digits='Product Unit of Measure', compute=_compute_product_qty)

    finished_lot_ids = fields.One2many(
        'stock.production.lot', 'consumption_finished_id', string='Finished Lot/Serial Number')
    rejected_lot_ids = fields.One2many(
        'stock.production.lot', 'consumption_rejected_id', string='Rejected Lot/Serial Number')
    byproduct_lot_ids = fields.One2many(
        'stock.production.lot', 'consumption_byproduct_id', string='ByProduct Lot/Serial Number')

    branch_id = fields.Many2one(
        'res.branch', string="Branch", store=True, readonly=True,
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', store=True, readonly=True,
        default=lambda self: self.env.company, tracking=True)

    move_raw_ids = fields.One2many(
        'stock.move', 'mrp_consumption_id', 'Components', readonly=True,
        states={'draft': [('readonly', False)]})
    byproduct_ids = fields.One2many(
        'stock.move', 'mrp_consumption_byproduct_id', 'By-Products', readonly=True,
        states={'draft': [('readonly', False)]})
    move_finished_ids = fields.One2many(
        'stock.move', 'mrp_consumption_finished_id', 'Finished', readonly=True,
        states={'draft': [('readonly', False)]})

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approval', 'To be Approved '),
        ('approved', 'Approved'),
        ('reject', 'Rejected '),
        ('confirm', 'Confirmed')
    ], string='Status', default='draft', tracking=True)

    date_finished = fields.Datetime('Date Finished', readonly=True)
    is_last_workorder = fields.Boolean(string='Is Last Workorder', readonly=True)
    product_tracking = fields.Selection(related='product_id.tracking')

    is_disable_generate = fields.Boolean(compute=_compute_is_disable_generate)
    consumption = fields.Selection(related='manufacturing_order_id.bom_id.consumption')

    picking_type_id = fields.Many2one('stock.picking.type', related='manufacturing_order_id.picking_type_id')
    location_src_id = fields.Many2one('stock.location', related='workorder_id.location_id')
    location_dest_id = fields.Many2one('stock.location', related='manufacturing_order_id.location_dest_id')
    production_location_id = fields.Many2one('stock.location', related='manufacturing_order_id.production_location_id')
    procurement_group_id = fields.Many2one('procurement.group', related='manufacturing_order_id.procurement_group_id')

    operation_id = fields.Many2one('mrp.routing.workcenter', related='workorder_id.operation_id', store=True)
    workcenter_id = fields.Many2one('mrp.workcenter', related='workorder_id.workcenter_id', store=True)

    is_locked = fields.Boolean(string='Locked', readonly=True)
    is_dedicated = fields.Boolean(string='Dedicated Material', readonly=True)

    # technical fields
    is_autogenerate = fields.Boolean(compute=_compute_is_autogenerate)

    state_1 = fields.Selection(related='state', tracking=False, string='State 1')
    state_2 = fields.Selection(related='state', tracking=False, string='State 2')
    state_3 = fields.Selection(related='state', tracking=False, string='State 3')
    state_4 = fields.Selection(related='state', tracking=False, string='State 4')

    show_byproduct_lot_tab = fields.Boolean(compute=_compute_byproduct_products)
    byproduct_manual_product_ids = fields.Many2many('product.product', compute=_compute_byproduct_products)
    default_byproduct_lot_qty = fields.Text(compute=_compute_byproduct_products)
    default_next_byproduct_product_id = fields.Many2one('product.product', compute=_compute_byproduct_products) 
    any_byproduct_is_autogenerate = fields.Boolean(compute=_compute_byproduct_products)
    all_byproduct_is_autogenerate = fields.Boolean(compute=_compute_byproduct_products)

    show_finished_lot_tab = fields.Boolean(compute=_compute_finished_products)
    finished_manual_product_ids = fields.Many2many('product.product', compute=_compute_finished_products)
    rejected_manual_product_ids = fields.Many2many('product.product', compute=_compute_finished_products)
    default_finished_lot_qty = fields.Text(compute=_compute_finished_products)
    default_rejected_lot_qty = fields.Text(compute=_compute_finished_products)
    default_next_finished_product_id = fields.Many2one('product.product', compute=_compute_finished_products) 
    default_next_rejected_product_id = fields.Many2one('product.product', compute=_compute_finished_products) 
    any_finished_is_autogenerate = fields.Boolean(compute=_compute_finished_products)
    all_finished_is_autogenerate = fields.Boolean(compute=_compute_finished_products)

    bom_finished_type = fields.Selection(related='workorder_id.bom_finished_type')

    def on_scaled(self):
        super(MrpConsumption, self).on_scaled()
        self._onchange_product_qty()
        action = None
        if self.env.context.get('pop_back', False):
            action = self.workorder_id.action_open_consumption(res_id=self.id)
            action['views'] = [[action['view_id'], action['view_mode']]]
        return action

    @api.onchange('finished_qty', 'rejected_qty', 'product_uom_id')
    def _onchange_product_qty(self):
        moves_todo = (self.move_raw_ids | self.byproduct_ids | self.move_finished_ids).filtered(
            lambda m: m._is_bom_move() and m.state not in ('done', 'cancel'))
        moves_todo._set_mpr_quantities()

        product_qty = self.finished_qty + self.rejected_qty

        """ We do not want moves to be splitted for partial finished quantity, except for rejected goods """
        for move in moves_todo:
            if not move._has_finished_line():
                move.product_uom_qty = move.quantity_done
            else:
                move.product_uom_qty = product_qty

    @api.onchange('finished_qty', 'rejected_qty', 'is_autogenerate')
    def _onchange_lot_serial_numbers(self):
        if not self.is_autogenerate:
            return

        tracking = self.product_id.tracking
        for ttype in ('finished', 'rejected'):
            lot_ids = self[ttype + '_lot_ids']
            to_generate_qty = self[ttype + '_qty']

            generated_qty = sum(lot_ids.mapped('consumption_qty'))
            qty_to_remove = generated_qty - to_generate_qty

            if qty_to_remove <= 0:
                continue
            
            lot_values = []
            for lot in lot_ids[::-1]:
                if lot.consumption_qty <= qty_to_remove:
                    lot_values += [(2, lot.id)]
                    qty_to_remove -= lot.consumption_qty
                else:
                    lot_values += [(1, lot.id, {'consumption_qty': lot.consumption_qty - qty_to_remove})]
                    break

            if lot_values:
                self[ttype + '_lot_ids'] = lot_values


    @api.onchange('byproduct_ids')
    def _onchange_byproducts(self):
        auto_byproducts = self.byproduct_ids.filtered(lambda b: b.product_id._is_auto_generate())
        if not auto_byproducts:
            return

        byproduct_lots = self.byproduct_lot_ids
        lot_values = []
        for product_id in auto_byproducts.mapped('product_id'):
            if not product_id._is_auto_generate():
                continue

            byproduct_ids = auto_byproducts.filtered(lambda b: b.product_id == product_id)
            to_generate_qty = sum(byproduct_ids.mapped('quantity_done'))
            
            lot_ids = byproduct_lots.filtered(lambda l: l.product_id == product_id)
            generated_qty = sum(lot_ids.mapped('consumption_qty'))

            qty_to_remove = generated_qty - to_generate_qty

            if qty_to_remove <= 0:
                continue

            for lot in lot_ids[::-1]:
                if lot.consumption_qty <= qty_to_remove:
                    lot_values += [(2, lot.id)]
                    qty_to_remove -= lot.consumption_qty
                else:
                    lot_values += [(1, lot.id, {'consumption_qty': lot.consumption_qty - qty_to_remove})]
                    break

        if lot_values:
            self.byproduct_lot_ids = lot_values

    def _get_product_quantity(self, bom_data, move):
        self.ensure_one()
        if not move._is_bom_move():
            return 0.0
        
        bom_product_uom = self.env['uom.uom'].browse(bom_data['product_uom_id']['id'])
        if move._has_bom_line():
            line = _find(bom_data['bom_line_ids'], move.origin_bom_line_id)
        elif move._has_byproduct():
            line = _find(bom_data['byproduct_ids'], move.origin_byproduct_id)
        elif move._has_finished_line():
            line = _find(bom_data['finished_ids'], move.origin_finished_id)
        else:
            return 0.0

        line_product_qty = line['product_qty']
        line_product_uom = self.env['uom.uom'].browse(line['product_uom_id']['id'])

        original_ratio = line_product_qty / bom_data['product_qty']
        mpr_qty = self.product_uom_id._compute_quantity(self.product_qty, bom_product_uom)
        return line_product_uom._compute_quantity(mpr_qty * original_ratio, move.product_uom)

    def button_confirm(self):
        self.ensure_one()

        err_message, action = self._pre_button_confirm(
            check_default=not self.env.company.production_record_conf,
            do_check_consumption=True)
        
        if err_message:
            raise UserError(err_message)
        if action:
            return action

        self._action_confirm()
        self._check_workorder()

        if self.env.context.get('pop_back'):
            return self.workorder_id.action_open_consumption(res_id=self.id)

    def _check_workorder(self):
        self.ensure_one()
        workorder = self.workorder_id
        workorder.qty_produced += self.product_uom_id._compute_quantity(self.product_qty, workorder.product_uom_id)
        if float_compare(workorder.qty_remaining, 0.0, precision_rounding=workorder.product_uom_id.rounding) <= 0:
            self._finish_workorder()
        else:
            self._hold_workorder()

    def _finish_workorder(self):
        self.ensure_one()
        self.workorder_id.button_finish()

        finished_moves = self.byproduct_ids | self.move_finished_ids
        if finished_moves:
            material_move_lines = self.manufacturing_order_id.move_raw_ids.filtered(lambda o: o.state == 'done').move_line_ids
            for move_line in finished_moves.move_line_ids:
                move_line.consume_line_ids = [(4, material_move_line.id) for material_move_line in material_move_lines]

    def _hold_workorder(self):
        self.ensure_one()
        self.workorder_id.end_all()
        if self.manufacturing_order_id.bom_operation_start_mode == 'adaptive':
            self.workorder_id.next_work_order_id.state = 'ready'

    def _handle_tracking(self, moves, qty_to_produce, lot_producing_ids):
        for lot_producing_id in lot_producing_ids:
            lot_producing_id.expiration_date = lot_producing_id.mrp_consumption_expiration_date

        for move in moves:
            tracking = move.product_id.tracking

            if tracking == 'serial':
                arange = len(lot_producing_ids)
                qty_done = [1.0] * arange
            elif tracking == 'lot':
                if move.product_id._is_lot_auto_generate():
                    arange = 1
                    qty_done = [qty_to_produce]
                else:
                    arange = len(lot_producing_ids)
                    qty_done = [lot.consumption_qty for lot in lot_producing_ids]
            else:
                arange = 1
                qty_done = [qty_to_produce]

            values = [(5,)]
            for i in range(arange):
                vals = move._prepare_move_line_vals(quantity=0)
                vals['qty_done'] = qty_done[i]

                if tracking in ('lot', 'serial'):
                    if tracking == 'serial':
                        vals['product_uom_id'] = move.product_uom.id

                    if i < len(lot_producing_ids):
                        vals['lot_id'] = lot_producing_ids[i].id

                values += [(0, 0, vals)]
            move.move_line_ids = values

    def _pre_button_confirm(self, check_default=True, do_check_consumption=False):
        self.ensure_one()

        if check_default:
            if self.is_last_workorder:
                # check fg tracking
                tracking_finished = self.move_finished_ids.filtered(lambda b: b.product_id.tracking in ('lot', 'serial'))
                for product_id in tracking_finished.mapped('product_id'):
                    to_generate_qty = sum(move.mpr_finished_qty + move.mpr_rejected_qty for move in tracking_finished.filtered(lambda b: b.product_id == product_id))
                    generated_qty = sum((self.finished_lot_ids | self.rejected_lot_ids).filtered(lambda l: l.product_id == product_id).mapped('consumption_qty'))
                    if to_generate_qty != generated_qty:
                        err_message = _('The amount of generated lot/serial number for finished/rejected product is not the same as produced quantity!\nGenerate/delete some lot/serial number first!')
                        return err_message, False

            # check byproduct tracking
            tracking_byproducts = self.byproduct_ids.filtered(lambda b: b.product_id.tracking in ('lot', 'serial'))
            for product_id in tracking_byproducts.mapped('product_id'):
                to_generate_qty = sum(tracking_byproducts.filtered(lambda b: b.product_id == product_id).mapped('quantity_done'))
                generated_qty = sum(self.byproduct_lot_ids.filtered(lambda l: l.product_id == product_id).mapped('consumption_qty'))
                if to_generate_qty != generated_qty:
                    err_message = _('The amount of generated lot/serial number for %s is not the same as produced quantity!\nGenerate/delete some lot/serial number first!' % product_id.display_name)
                    return err_message, False

            # check availability
            for move in self.move_raw_ids:
                if self.is_dedicated and move.quantity_done > move.product_id.uom_id._compute_quantity(move.dedicated_qty, move.product_uom):
                    err_message = _('Not enough stock reserved')
                    return err_message, False
                if move.quantity_done > move.availability_uom_qty + move.reserved_availability:
                    err_message = _('There is not enough stock for product %s on location %s' % (move.product_id.name, move.location_id.display_name))
                    return err_message, False

        if do_check_consumption:
            # check consumption
            confirmed = self.env.context.get('consumption_confirmed')
            if self.consumption == 'warning' and not confirmed:
                material_values, byproduct_values = self._get_not_expected_moves()
                if material_values or byproduct_values:
                    action = {
                        'name': 'Consumption Warning',
                        'type': 'ir.actions.act_window',
                        'res_model': 'mrp.flexible.consumption.warning',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_consumption_id': self.id,
                            'default_material_ids': material_values,
                            'default_byproduct_ids': byproduct_values
                        }
                    }
                    return False, action

        return False, False

    def _get_not_expected_moves(self):
        self.ensure_one()

        def get_moves(moves):
            not_expected_moves = []
            for move in moves:
                if not move._is_bom_move():
                    not_expected_moves += [(0, 0, create_vals(move))]
                    continue
                expected_qty = move.product_uom_qty
                if not move._has_byproduct():
                    if expected_qty != move.quantity_done:
                        not_expected_moves += [(0, 0, create_vals(move, expected_qty=expected_qty))]
                else:
                    line = _find(bom_data['byproduct_ids'], move.origin_byproduct_id)
                    if not line:
                        continue
                    if move._compare_expected_moves(consumption=self, expected_qty=expected_qty, line=line):
                        not_expected_moves += [(0, 0, move._prepare_not_expected_move_values(consumption=self, expected_qty=expected_qty, line=line))]
            return not_expected_moves

        bom_data = self.manufacturing_order_id._read_bom_data(origin=True)[self.manufacturing_order_id.bom_id.id]
        return get_moves(self.move_raw_ids), get_moves(self.byproduct_ids)

    def _update_manual_moves(self, moves):
        self.ensure_one()
        for move in moves:
            values = {
                'origin': self.manufacturing_order_id.name,
                'mrp_plan_id': self.manufacturing_plan.id,
                'workorder_id': self.workorder_id.id
            }
            warehouse_id = self.env['stock.warehouse']
            if move.mrp_consumption_id:
                values.update({'raw_material_production_id': self.manufacturing_order_id.id})
                warehouse_id = self.location_src_id.get_warehouse()
            elif move.mrp_consumption_byproduct_id:
                values.update({'production_id': self.manufacturing_order_id.id})
                warehouse_id = self.location_dest_id.get_warehouse()
            values.update({'warehouse_id': warehouse_id.id})
            move.update(values)

    def _prepare_moves(self):
        self.ensure_one()
        manual_moves = self.move_raw_ids.filtered(lambda m: not m._has_bom_line()) | self.byproduct_ids.filtered(lambda m: not m._has_byproduct())
        self._update_manual_moves(manual_moves)

        for move in manual_moves.filtered(lambda o: o.product_uom_qty == 0.0):
            move.product_uom_qty = move.quantity_done


    def _action_confirm(self):
        self.ensure_one()
        self._prepare_moves()

        order = self.manufacturing_order_id

        move_raw_ids = self.move_raw_ids.filtered(lambda o: o.product_uom_qty != 0.0 and o.state not in ('done', 'cancel'))
        move_raw_ids._action_done()

        byproduct_ids = self.byproduct_ids.filtered(lambda o: o.product_uom_qty != 0.0 and o.state not in ('done', 'cancel'))
        tracking_byproduct_ids = byproduct_ids.filtered(lambda b: b.product_id.tracking in ('lot', 'serial'))
        byproduct_lot_ids = self.byproduct_lot_ids
        for product in set(tracking_byproduct_ids.mapped('product_id')):
            product_byproduct_ids = tracking_byproduct_ids.filtered(lambda m: m.product_id == product)
            product_byproduct_qty = sum(product_byproduct_ids.mapped('quantity_done'))
            product_byproduct_lots = byproduct_lot_ids.filtered(lambda b: b.product_id == product)
            self._handle_tracking(product_byproduct_ids, product_byproduct_qty, product_byproduct_lots)
        
        if tracking_byproduct_ids:
            tracking_byproduct_ids._action_done()
        
        non_tracking_byproduct_ids = byproduct_ids - tracking_byproduct_ids
        if non_tracking_byproduct_ids:
            non_tracking_byproduct_ids._action_done()

        move_finished_ids = self.move_finished_ids.filtered(lambda o: o.product_uom_qty != 0.0 and o.state not in ('done', 'cancel'))
        tracking_finished_ids = move_finished_ids.filtered(lambda b: b.product_id.tracking in ('lot', 'serial'))
        finished_lot_ids = self.finished_lot_ids
        for product in set(tracking_finished_ids.mapped('product_id')):
            product_finished_ids = tracking_finished_ids.filtered(lambda m: m.product_id == product)
            product_finished_qty = sum(product_finished_ids.mapped('mpr_finished_qty'))
            product_finished_lots = finished_lot_ids.filtered(lambda b: b.product_id == product)
            self._handle_tracking(product_finished_ids, product_finished_qty, product_finished_lots)
        
        if tracking_finished_ids:
            tracking_finished_ids._action_done()
        
        non_tracking_finished_ids = move_finished_ids - tracking_finished_ids
        if non_tracking_finished_ids:
            non_tracking_finished_ids._action_done()

        move_rejected_ids = self.move_finished_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        if move_rejected_ids:
            bom = order.bom_id
            rejected_product = order.rejected_product_id or bom.rejected_product_id
            if not rejected_product:
                raise ValidationError(_('Please set rejected goods!'))
            location_rejected_id = self.manufacturing_order_id.rejected_location_dest_id
            move_rejected_ids.write({
                'product_id': rejected_product.id,
                'warehouse_id': location_rejected_id.get_warehouse().id,
                'location_dest_id': location_rejected_id.id,
                'is_mpr_rejected': True
            })

            tracking_rejected_ids = move_rejected_ids.filtered(lambda b: b.product_id.tracking in ('lot', 'serial'))
            
            rejected_lot_ids = self.rejected_lot_ids
            for product in set(tracking_rejected_ids.mapped('product_id')):
                product_rejected_ids = tracking_rejected_ids.filtered(lambda o: o.product_id == product)
                product_rejected_qty = sum(product_rejected_ids.mapped('mpr_rejected_qty'))
                product_rejected_lots = rejected_lot_ids.filtered(lambda b: b.product_id == product)
                self._handle_tracking(product_rejected_ids, product_rejected_qty, product_rejected_lots)

            if tracking_rejected_ids:
                tracking_rejected_ids._action_done()

            non_tracking_rejected_ids = move_rejected_ids - tracking_rejected_ids
            if non_tracking_rejected_ids:
                for move in non_tracking_rejected_ids:
                    move.quantity_done = move.product_uom_qty
                non_tracking_rejected_ids._action_done()

        if self.is_last_workorder:
            order.write({
                'finished_product_qty': order.finished_product_qty + self.finished_qty,
                'rejected_product_qty': order.rejected_product_qty + self.rejected_qty
            })
        self.state = 'confirm'

    def _get_expiration_date(self):
        self.ensure_one()
        return False

    def action_generate_serial(self):
        self.action_generate_serial_finished_goods()
        self.action_generate_serial_byproducts()
        if self.env.context.get('pop_back'):
            return self.workorder_id.action_open_consumption(res_id=self.id)

    def action_generate_serial_byproducts(self):
        self.ensure_one()
        byproduct_product_ids = self.byproduct_ids.mapped('product_id').filtered(lambda p: p._is_auto_generate())
        if not byproduct_product_ids:
            return
        
        exp_date = self._get_expiration_date()
        lot_values = []
        for product in byproduct_product_ids:
            lot_ids = self.byproduct_lot_ids.filtered(lambda b: b.product_id == product)
            generated_qty = sum(lot_ids.mapped('consumption_qty'))
            to_generate_qty = sum(self.byproduct_ids.filtered(lambda b: b.product_id == product).mapped('quantity_done')) - generated_qty

            if to_generate_qty <= 0.0:
                continue

            if product.tracking == 'serial':
                lot_values += [(4, product.create_next_lot_and_serial(1.0, expiration_date=exp_date).id) for i in range(int(to_generate_qty))]
            else:
                if lot_ids:
                    lot_values += [(1, lot_ids[-1].id, {'consumption_qty': lot_ids[-1].consumption_qty + to_generate_qty})]
                else:
                    lot_values += [(4, product.create_next_lot_and_serial(to_generate_qty, expiration_date=exp_date).id)]
        if lot_values:
            self.byproduct_lot_ids = lot_values

    def action_generate_serial_finished_goods(self):
        self.ensure_one()
        finished_product_ids = self.move_finished_ids.mapped('product_id').filtered(lambda p: p._is_auto_generate())
        if not finished_product_ids:
            return
        
        exp_date = self._get_expiration_date()
        finished_lot_values, rejected_lot_values = [], []
        for product in finished_product_ids:
            finished_lots = self.finished_lot_ids.filtered(lambda b: b.product_id == product)
            finished_generated_qty = sum(finished_lots.mapped('consumption_qty'))
            finished_to_generate_qty = sum(self.move_finished_ids.filtered(lambda b: b.product_id == product).mapped('mpr_finished_qty')) - finished_generated_qty

            if finished_to_generate_qty > 0.0:
                if product.tracking == 'serial':
                    finished_lot_values += [(4, product.create_next_lot_and_serial(1.0, expiration_date=exp_date).id) for i in range(int(finished_to_generate_qty))]
                else:
                    if finished_lots:
                        finished_lot_values += [(1, finished_lots[-1].id, {'consumption_qty': finished_lots[-1].consumption_qty + finished_to_generate_qty})]
                    else:
                        finished_lot_values += [(4, product.create_next_lot_and_serial(finished_to_generate_qty, expiration_date=exp_date).id)]
            
            rejected_lots = self.rejected_lot_ids.filtered(lambda b: b.product_id == product)
            rejected_generated_qty = sum(rejected_lots.mapped('consumption_qty'))
            rejected_to_generate_qty = sum(self.move_finished_ids.filtered(lambda b: b.product_id == product).mapped('mpr_rejected_qty')) - rejected_generated_qty

            if rejected_to_generate_qty > 0.0:
                if product.tracking == 'serial':
                    rejected_lot_values += [(4, product.create_next_lot_and_serial(1.0, expiration_date=exp_date).id) for i in range(int(rejected_to_generate_qty))]
                else:
                    if rejected_lots:
                        rejected_lot_values += [(1, rejected_lots[-1].id, {'consumption_qty': rejected_lots[-1].consumption_qty + rejected_to_generate_qty})]
                    else:
                        rejected_lot_values += [(4, product.create_next_lot_and_serial(rejected_to_generate_qty, expiration_date=exp_date).id)]

        if finished_lot_values:
            self.finished_lot_ids = finished_lot_values
        if rejected_lot_values:
            self.rejected_lot_ids = rejected_lot_values

    @api.model
    def _default_approval_matrix(self, company=None, branch=None):
        if not company:
            company = self.env.company
        if not company.production_record_conf:
            return False

        default = self.env.context.get('default_approval_matrix_id', False)
        if default:
            return default

        if not branch:
            branch = self.env.user.branch_id
        return self.env['mrp.approval.matrix'].search([
            ('company_id', '=', company.id),
            ('branch_id', '=', branch.id),
            ('matrix_type', '=', 'pr')
        ], limit=1).id

    @api.depends('approval_matrix_id', 'is_matrix_on')
    def _compute_approval_matrix_lines(self):
        for record in self:
            lines = [(5,)]
            if record.is_matrix_on:
                for line in record.approval_matrix_id.line_ids:
                    lines += [(0, 0, {
                        'pr_id': record.id,
                        'line_id': line.id,
                        'sequence': line.sequence,
                        'minimum_approver': line.minimum_approver,
                        'approver_ids': [(6, 0, line.approver_ids.ids)]
                    })]
            record.approval_matrix_line_ids = lines

    @api.depends('approval_matrix_line_ids', 'approval_matrix_line_ids.need_action_ids', 'is_matrix_on')
    def _compute_user_is_approver(self):
        user = self.env.user
        for record in self:
            need_action_ids = record.approval_matrix_line_ids.mapped('need_action_ids')
            record.user_is_approver = user in need_action_ids and record.is_matrix_on

    @api.depends('state', 'is_matrix_on')
    def _compute_hide_confirm_btn(self):
        for record in self:
            state = record.state
            use_matrix = record.is_matrix_on
            is_hide = (not use_matrix and state == 'confirm') or (use_matrix and state != 'approved')
            record.hide_confirm_btn = is_hide

    is_matrix_on = fields.Boolean(related='company_id.production_record_conf')

    approval_matrix_id = fields.Many2one(
        comodel_name='mrp.approval.matrix', 
        domain="""[
            ('matrix_type', '=', 'pr'),
            ('branch_id', '=', branch_id),
            ('company_id', '=', company_id)
        ]""",
        string='Approval Matrix', 
        default=_default_approval_matrix)
    approval_matrix_line_ids = fields.One2many(
        comodel_name='mrp.approval.matrix.entry',
        inverse_name='pr_id',
        string='Approval Matrix Lines',
        compute=_compute_approval_matrix_lines,
        store=True)
    
    user_is_approver = fields.Boolean(compute=_compute_user_is_approver)
    hide_confirm_btn = fields.Boolean(compute=_compute_hide_confirm_btn)

    @api.onchange('company_id', 'branch_id')
    def onchange_company_branch(self):
        self.approval_matrix_id = self._default_approval_matrix(company=self.company_id, branch=self.branch_id)
    
    def action_approval(self):
        self.ensure_one()
        if not self.is_matrix_on:
            return

        # data checking (e.g. material availability, product tracking, & accounting data) 
        # executed here when matrix is on and executed in button_confirm when matrix is off
        err_message, action = self._pre_button_confirm()
        if err_message:
            raise UserError(err_message)

        options = {
            'post_log': True,
            'send_system': True,
            'send_email': True,
            'send_whatsapp': self.company_id.send_wa_approval_notification_mpr
        }
        self.approval_matrix_id.action_approval(self, options=options)
        self.write({'state': 'approval'})
        if self.env.context.get('pop_back'):
            return self.workorder_id.action_open_consumption(res_id=self.id)

    def action_approve(self):
        self.ensure_one()
        if not self.is_matrix_on:
            return
        self.approval_matrix_id.action_approve(self)
        if all(l.state == 'approved' for l in self.approval_matrix_line_ids):
            self.write({'state': 'approved'})
        if self.env.context.get('pop_back'):
            return self.workorder_id.action_open_consumption(res_id=self.id)

    def action_reject(self, reason=False):
        self.ensure_one()
        if not self.is_matrix_on:
            return
        result = self.approval_matrix_id.action_reject(self, reason=reason)
        if result is not True:
            return result
        
        manual_moves = (self.move_raw_ids | self.byproduct_ids).filtered(lambda m: not m._is_bom_move())
        self._update_manual_moves(manual_moves)

        for move in self.move_raw_ids | self.byproduct_ids | self.move_finished_ids:
            move.write({
                'quantity_done': 0.0,
                'product_uom_qty': move.product_uom_qty
            })
            move._action_cancel()
        self.workorder_id.end_all()

        if any(l.state == 'rejected' for l in self.approval_matrix_line_ids):
            self.write({'state': 'reject'})
        if self.env.context.get('pop_back'):
            return self.workorder_id.action_open_consumption(res_id=self.id)
