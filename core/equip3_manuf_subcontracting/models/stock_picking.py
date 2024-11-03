import json
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    @api.depends('subcon_production_id', 'is_a_subcontracting')
    def _compute_production_name(self):
        for record in self:
            name = ''
            production_id = record.subcon_production_id
            if record.is_a_subcontracting and production_id:
                name = '%s - %s' % (production_id.name, production_id.product_id.name)
            record.subcon_production_name = name

    @api.depends('is_a_subcontracting', 'subcon_byproduct_ids', 'subcon_byproduct_ids.subcon_quantity_done')
    def _compute_subcon_qty_producing(self):
        for record in self:
            record.set_subcon_qty_producing()

    def _inverse_subcon_qty_producing(self):
        for record in self:
            record.set_subcon_fg_line_qty_done()

    is_a_delivery = fields.Boolean(string='Is a Delivery')
    is_a_subcontracting = fields.Boolean(string='Is a Subcontracting')
    subcon_production_id = fields.Many2one('mrp.production', string='Production Order')
    subcon_production_name = fields.Char(string='Production Order Name', compute=_compute_production_name, store=True)
    subcon_product_qty = fields.Float(string='Subcontract Quantity', digits='Product Unit of Measure', copy=False)
    subcon_qty_producing = fields.Float(string='Subcontract Producing Quantity', digits='Product Unit of Measure', compute=_compute_subcon_qty_producing, inverse=_inverse_subcon_qty_producing, store=True, copy=False)
    subcon_qty_produced = fields.Float(string='Subcontract Produced Quantity', digits='Product Unit of Measure', copy=False)
    subcon_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    subcon_byproduct_ids = fields.One2many('stock.move', 'subcon_picking_id', 'Subcontracting By-Products')
    subcon_requisition_id = fields.Many2one('purchase.requisition', string='Subcon Blanket Order')
    is_readonly_origin = fields.Boolean()

    subcon_material_workorder_ids = fields.One2many('mrp.workorder', 'subcon_material_picking_id', string='Subcontracting Workorders Material')
    subcon_finished_workorder_ids = fields.One2many('mrp.workorder', 'subcon_finished_picking_id', string='Subcontracting Workorders Finished Goods')

    @api.constrains('is_a_subcontracting')
    def is_a_subcontracting_constraints(self):
        for record in self:
            if not record.is_a_subcontracting:
                continue
            missing_field = False
            if not record.subcon_production_id:
                missing_field = 'Production Order (subcon_production_id)'
            if not record.subcon_uom_id:
                missing_field = 'Subcontracting UoM (subcon_uom_id)'
            if missing_field:
                raise ValidationError(_('%s is mandatory when Subcontracting is True!' % missing_field))

    def _action_done(self):
        moves_to_delete = self.env['stock.move']
        consumption_to_confirm = self.env['mrp.consumption']
        move_maps = {}
        for record in self.filtered(lambda o: o.is_a_subcontracting):
            if record.picking_type_code == 'internal':
                for workorder in record.subcon_material_workorder_ids:
                    workorder.button_start()
                    res = workorder.button_finish_wizard()
                    if res is None:
                        consumption = workorder.consumption_ids.filtered(lambda o: o.state != 'confirm')
                    else:
                        consumption = self.env['mrp.consumption'].browse(res['res_id'])
                    moves_to_delete |= consumption.move_raw_ids.filtered(lambda o: not o.subcon_move_id)
                
                move_vals_list = []
                for move in record.move_ids_without_package:
                    subcon_move = move.subcon_move_id
                    move_vals_list += [(1, move.id, {
                        'mrp_workorder_component_id': subcon_move.mrp_workorder_component_id.id,
                        'raw_material_production_id': subcon_move.raw_material_production_id.id,
                        'mrp_plan_id': subcon_move.raw_material_production_id.mrp_plan_id.id,
                        'bom_line_id': subcon_move.bom_line_id.id,
                        'origin_bom_line_id': subcon_move.bom_line_id.id,
                        'mrp_consumption_id': subcon_move.mrp_consumption_id.id
                    })]
                    move_maps[subcon_move] = move

                record.move_ids_without_package = move_vals_list

            elif record.picking_type_code == 'incoming':
                production_id = record.subcon_production_id

                qty_producing = record.subcon_qty_producing
                qty_produced = record.subcon_qty_produced

                move_vals_list = []
                for move in record.move_ids_without_package:
                    subcon_move = move.subcon_move_id
                    move_vals_list += [(1, move.id, {
                        'workorder_id': subcon_move.workorder_id.id,
                        'mrp_workorder_byproduct_id': subcon_move.mrp_workorder_byproduct_id.id,
                        'production_id': subcon_move.production_id.id,
                        'mrp_plan_id': subcon_move.production_id.mrp_plan_id.id,
                        'byproduct_id': subcon_move.byproduct_id.id,
                        'finished_id': subcon_move.finished_id.id,
                        'origin_byproduct_id': subcon_move.byproduct_id.id,
                        'origin_finished_id': subcon_move.finished_id.id,
                        'mrp_consumption_byproduct_id': subcon_move.mrp_consumption_byproduct_id.id,
                        'mrp_consumption_finished_id': subcon_move.mrp_consumption_finished_id.id
                    })]
                
                record.move_ids_without_package = move_vals_list

                for workorder in record.subcon_finished_workorder_ids:
                    consumptions = workorder.consumption_ids.filtered(lambda c: c.state not in ('confirm', 'reject'))
                    if not consumptions:
                        raise ValidationError(_('Please validate subcontracting material transfer first!'))
                    
                    consumption = consumptions[0]
                    moves_to_delete |= (consumption.move_finished_ids | consumption.byproduct_ids).filtered(lambda o: not o.subcon_move_id)
                    consumption_to_confirm |= consumption

                material_cost, move_costs = production_id._get_and_predict_cost()
                byproduct_cost = 0.0
                for move in production_id.move_byproduct_ids.filtered(lambda o: o not in moves_to_delete):
                    byproduct_cost += (move.allocated_cost * material_cost) / 100
                finished_cost = material_cost - byproduct_cost

                for move in record.move_ids_without_package:
                    subcon_move = move.subcon_move_id
                    if subcon_move.byproduct_id:
                        cost = (move.allocated_cost * material_cost) / 100
                    else:
                        cost = (move.allocated_cost * finished_cost) / 100
                    price_unit = cost / move.product_qty
                    move.price_unit = price_unit

                record.write({'subcon_qty_produced': qty_produced + qty_producing})

        res = super(StockPickingInherit, self)._action_done()

        if moves_to_delete:
            moves_to_delete._action_cancel()
            moves_to_delete.unlink()

        for consumption in consumption_to_confirm:
            lot_move_lines_pairs = defaultdict(lambda: self.env['stock.move.line'])
            for move in (consumption.move_finished_ids | consumption.byproduct_ids):
                move.mpr_finished_qty = move.quantity_done
                
                for move_line in move.move_line_ids:
                    lot = move_line.lot_id
                    if not lot:
                        continue
                    lot_move_lines_pairs[lot] |= move_line

            for lot, move_lines in lot_move_lines_pairs.items():
                consumption_qty = sum(move_lines.mapped('qty_done'))
                write_values = {'consumption_qty': consumption_qty}
                if move_lines.filtered(lambda o: o.move_id.byproduct_id):
                    write_values.update({'consumption_byproduct_id': consumption.id})
                if move_lines.filtered(lambda o: o.move_id.finished_id):
                    write_values.update({'consumption_finished_id': consumption.id})
                lot.write(write_values)

            consumption.button_confirm()

        return res

    def _create_backorder(self):
        backorders = super(StockPickingInherit, self)._create_backorder()

        for backorder in backorders:
            if not backorder.is_a_subcontracting:
                continue

            # copy subcon_byproduct_ids
            subcon_byproduct_ids = self.env['stock.move']
            for move in backorder.backorder_id.subcon_byproduct_ids:
                new_move = move.copy({
                    'mrp_plan_id': False,
                    'raw_material_production_id': False,
                    'production_id': False,
                    'mrp_workorder_component_id': False,
                    'mrp_workorder_byproduct_id': False,
                    'product_uom_qty': 1.0,
                    'subcon_quantity_done': 0.0,
                    'quantity_done': 0.0
                })
                subcon_byproduct_ids |= new_move
            backorder.subcon_byproduct_ids = [(6, 0, subcon_byproduct_ids.ids)]

            # calculate produced nested backorder
            origin = backorder
            qty_produced = 0.0
            while origin.backorder_id:
                origin = origin.backorder_id
                qty_produced += origin.subcon_qty_producing

            product_qty = origin.subcon_product_qty
            backorder.write({
                'subcon_product_qty': product_qty,
                'subcon_qty_produced': qty_produced,
                'subcon_qty_producing': product_qty - qty_produced
            })

        return backorders

    def set_subcon_qty_producing(self):
        self.ensure_one()
        qty_producing = 0.0
        if self.is_a_subcontracting:
            qty_producing = self.subcon_product_qty - self.subcon_qty_produced
            if self.subcon_byproduct_ids:
                qty_producing = sum(self.subcon_byproduct_ids.mapped('subcon_quantity_done'))
        self.subcon_qty_producing = qty_producing

    def validate_subcon_qty_producing(self):
        self.ensure_one()
        max_qty = self.subcon_product_qty - self.subcon_qty_produced
        min_qty = min(1.0, max_qty)
        if not min_qty <= self.subcon_qty_producing <= max_qty:
            message = _('Subcontracted must be at: %s <= Subcontracted <= %s!' % (min_qty, max_qty))
            raise ValidationError(message)

    def set_subcon_fg_line_qty_done(self):
        self.ensure_one()
        if not self.is_a_subcontracting:
            return
        byproduct_qty = sum(self.subcon_byproduct_ids.filtered(lambda b: not b.subcon_is_finished_good).mapped('subcon_quantity_done'))
        self.subcon_byproduct_ids.filtered(lambda b: b.subcon_is_finished_good).subcon_quantity_done = self.subcon_qty_producing - byproduct_qty

    def set_move_ids_without_package_from_subcon(self, validate=False):
        self.ensure_one()
        if not self.is_a_subcontracting:
            return
        if validate:
            self.validate_subcon_qty_producing()
        try:
            ratio = self.subcon_qty_producing / (self.subcon_product_qty - self.subcon_qty_produced)
        except ZeroDivisionError:
            ratio = 1.0
        for move in self.move_ids_without_package:
            move.update({'quantity_done': move.product_uom_qty * ratio})

    @api.constrains('subcon_qty_producing')
    def force_move_ids_without_package_from(self):
        for record in self:
            record.set_move_ids_without_package_from_subcon(validate=True)

    @api.onchange('subcon_qty_producing')
    def onchange_subcon_qty_producing(self):
        self.set_subcon_fg_line_qty_done()
        self.set_move_ids_without_package_from_subcon()

    def button_validate(self):
        for record in self:
            if not record.is_a_subcontracting:
                continue

            byproduct_ids = record.subcon_byproduct_ids.filtered(lambda m: not m.subcon_is_finished_good)
            total_allocated_cost = sum(byproduct_ids.mapped('allocated_cost'))
            if total_allocated_cost > 100:
                raise UserError(_('Total By-Products Allocated Cost must be less or equal to 100%!'))

            elif total_allocated_cost < 100:
                if any(move.subcon_quantity_done <= 0 for move in byproduct_ids):
                    raise UserError(_('One or more byproduct(s) has <= 0.0 quantity, it will not recorded on MPR!'))

        res = super(StockPickingInherit, self).button_validate()
        for line in self.move_ids_without_package:
            if line.move_line_nosuggest_ids:
                for i in line.move_line_nosuggest_ids:
                    lot = i.lot_id
                    lot.sudo().write({
                        'length': i.length,
                        'height': i.height,
                        'width': i.width,
                    })
        return res


class MRPSubcontractingByProduct(models.Model):
    _name = 'mrp.subcon.byproduct'
    _description = 'MRP Subcontracting By-Product'

    picking_id = fields.Many2one('stock.picking', string='Picking')
    is_finished_good = fields.Boolean()
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    allocated_cost = fields.Float('Allocated Cost (%)')

    def create_moves(self):
        stock_move_ids = self.env['stock.move']
        for record in self:
            if record.is_finished_good:
                continue
            production_id = record.picking_id.subcon_production_id
            move_values = production_id._get_move_finished_values(
                record.product_id.id,
                record.product_qty,
                record.product_uom_id.id
            )
            move_values.update({'quantity_done': record.product_qty})
            stock_move_ids |= self.env['stock.move'].create(move_values)
        return stock_move_ids
