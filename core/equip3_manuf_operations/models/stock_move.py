# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import fields, models, api, _
from odoo.tools import float_compare
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    mrp_plan_id = fields.Many2one('mrp.plan', string='Manufacturing Plan')

    mrp_workorder_component_id = fields.Many2one('mrp.workorder', string='Work Order Material')
    mrp_workorder_byproduct_id = fields.Many2one('mrp.workorder', string='Work Order By-Product')

    production_byproduct_loc_id = fields.Many2one('stock.location', string='Produced in Location')
    location_rejected_id = fields.Many2one('stock.location', string='Rejected Location')
    finished_id = fields.Many2one('mrp.bom.finished', string='BoM Finished Line')

    """ This is simply available field in stock.move that converted to UoM move """
    availability_uom_qty = fields.Float(digits='Product Unit of Measure', compute='_compute_availability_uom')

    mrp_reserve_line_ids = fields.One2many('mrp.reserve.line', 'move_id', string='MRP Reserve Lines')
    mrp_reserve_next_sequence = fields.Integer(compute='_compute_mrp_reserve_next_sequence')

    is_material_qty_changed = fields.Boolean(string='Is Material Quantity Changed')

    unbuild_move_id = fields.Many2one('stock.move', string='Unbuild Origin Move')

    def _trigger_assign(self):
        """ We don't want `_action_done` auto assign mrp moves """
        self = self.with_context(exclude_mrp_moves=True)
        return super(StockMove, self)._trigger_assign()

    def _action_assign(self):
        moves_todo = self
        """ Exclude mrp moves if it's called from `_trigger_assign` """
        if self._context.get('exclude_mrp_moves', False):
            moves_todo = moves_todo.filtered(lambda m: not m.raw_material_production_id)
        return super(StockMove, moves_todo)._action_assign()

    def _action_confirm(self, merge=True, merge_into=False):
        new_merge = merge
        pickings = self.mapped('picking_id')
        if pickings and all(picking.is_transfer_good for picking in pickings):
            new_merge = False
        return super(StockMove, self)._action_confirm(merge=new_merge, merge_into=merge_into)

    @api.depends('product_id', 'product_uom', 'location_id')
    def _compute_availability_uom(self):
        for move in self:
            availability_uom_qty = 0.0
            if move.product_id and move.product_uom and move.location_id:
                availability_qty = move._get_available_quantity(move.location_id)
                availability_uom_qty = move.product_id.uom_id._compute_quantity(availability_qty, move.product_uom)
            move.availability_uom_qty = availability_uom_qty

    @api.depends('mrp_reserve_line_ids')
    def _compute_mrp_reserve_next_sequence(self):
        for record in self:
            record.mrp_reserve_next_sequence = len(record.mrp_reserve_line_ids) + 1

    def action_mrp_reserve_material_wizard(self):
        self.ensure_one()
        wizard_line_id = self.env.context.get('mrp_reserve_material_wizard_line', False)
        if not wizard_line_id:
            return

        wizard_line = self.env['mrp.reserve.material.line'].browse(wizard_line_id)

        if self.env.context.get('is_discard', False):
            self.mrp_reserve_line_ids.unlink()

        total_to_reserve_qty = sum(self.mrp_reserve_line_ids.mapped('product_qty'))
        if total_to_reserve_qty > self.product_qty:
            raise UserError(_('Cannot reserve more than the quantity in production!'))

        rounding = self.product_id.uom_id.rounding
        product_id = self.product_id
        location_id = self.location_id
        for line in self.mrp_reserve_line_ids:
            quants = self.env['stock.quant'].sudo()._gather(product_id, location_id, lot_id=line.lot_id)
            if float_compare(line.product_qty, 0, precision_rounding=rounding) > 0:
                available_quantity = sum(quants.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=rounding) > 0).mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
                if float_compare(line.product_qty, available_quantity, precision_rounding=rounding) > 0:
                    raise UserError(_("There's not enough stock for lot %s to reserve (available: %s)" % (line.lot_id.display_name, available_quantity)))
        
        wizard_line.write({'to_reserve_uom_qty': total_to_reserve_qty})
        
        return { 
            'type': 'ir.actions.act_window',
            'name': _('Partial Reserve Material'),
            'res_model': 'mrp.reserve.material',
            'target': 'new',
            'view_mode': 'form',
            'res_id': wizard_line.reserve_id.id
        }

    def _do_unreserve(self):
        result = super(StockMove, self)._do_unreserve()
        if not self.env.context.get('skip_unlink_reserved_lines', False):
            self.mrp_reserve_line_ids.unlink()
        return result

    """ 
    OPTIMIZATION
    functions bellow is not relevan anymore.
    """
    @api.depends('raw_material_production_id.lot_producing_id')
    def _compute_order_finished_lot_ids(self):
        self.order_finished_lot_ids = [(5,)]


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    unbuild_qty = fields.Float(string='Unbuild Quantity')
