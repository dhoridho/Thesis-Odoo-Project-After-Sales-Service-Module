from odoo import models, fields, api, _
from odoo.tools import float_round, OrderedSet
from odoo.exceptions import ValidationError


class StockMoveLine(models.Model):
	_inherit = 'stock.move.line'

	assembly_id = fields.Many2one('assembly.production.record', 'Asemble Order', check_company=True)


class StockMove(models.Model):
	_inherit = 'stock.move'

	@api.depends('product_id', 'warehouse_id', 'warehouse_id.lot_stock_id')
	def _compute_product_available_quantity(self):
		quant_id = self.env['stock.quant']
		for move in self:
			move.assembly_product_free_qty = 0.0
			if not move.product_id or not move.warehouse_id:
				continue
			move.assembly_product_free_qty = quant_id._get_available_quantity(
				move.product_id, move.warehouse_id.lot_stock_id
			)

	created_assembly_id = fields.Many2one('assembly.production.record', 'Created Assembly Order', check_company=True)
	assembly_finished_id = fields.Many2one('assembly.production.record', 'Assembly Order for finished products', check_company=True, index=True)
	assembly_component_id = fields.Many2one('assembly.production.record', 'Assembly Order for components',  check_company=True, index=True)
	
	assembly_unit_factor = fields.Float('Assembly Unit Factor', compute='_compute_assembly_unit_factor', store=True)
	assembly_should_consume_qty = fields.Float('Assembly Quantity To Consume', compute='_compute_assembly_should_consume_qty', digits='Product Unit of Measure')
	assembly_product_free_qty = fields.Float(compute=_compute_product_available_quantity, string='Assembly Available', digits='Product Unit of Measure')

	assembly_product_uom_qty = fields.Float('Assembly Demand',  digits='Product Unit of Measure', default=0.0, states={'done': [('readonly', True)]})
	assembly_quantity_done = fields.Float('Assembly Quantity Done', digits='Product Unit of Measure')

	@api.onchange('product_uom_qty')
	def _onchange_set_assembly_qty(self):
		if self.assembly_component_id:
			self.assembly_product_uom_qty = self.product_uom_qty

	@api.depends('product_uom_qty',
		'assembly_component_id', 'assembly_component_id.product_qty', 'assembly_component_id.rejected_qty',
		'assembly_finished_id', 'assembly_finished_id.product_qty', 'assembly_finished_id.rejected_qty')
	def _compute_assembly_unit_factor(self):
		for move in self:
			assembly_id = move.assembly_component_id or move.assembly_finished_id
			if assembly_id:
				move.assembly_unit_factor = move.product_uom_qty / ((assembly_id.product_qty + assembly_id.rejected_qty) or 1)
			else:
				move.assembly_unit_factor = 1.0

	@api.depends('assembly_component_id', 'assembly_component_id.name', 'assembly_finished_id', 'assembly_finished_id.name')
	def _compute_reference(self):
		moves_with_reference = self.env['stock.move']
		for move in self:
			if move.assembly_component_id and move.assembly_component_id.name:
				move.reference = move.assembly_component_id.name
				moves_with_reference |= move
			if move.assembly_finished_id and move.assembly_finished_id.name:
				move.reference = move.assembly_finished_id.name
				moves_with_reference |= move
		super(StockMove, self - moves_with_reference)._compute_reference()

	@api.depends('assembly_component_id.product_qty', 'assembly_component_id.rejected_qty', 'product_uom_qty', 'product_uom')
	def _compute_assembly_should_consume_qty(self):
		for move in self:
			ko = move.assembly_component_id
			if not ko or not move.product_uom:
				move.assembly_should_consume_qty = 0
				continue
			move.assembly_should_consume_qty = float_round((ko.product_qty + ko.rejected_qty) * move.assembly_unit_factor, precision_rounding=move.product_uom.rounding)

	@api.onchange('product_id')
	def onchange_product_id(self):
		super(StockMove, self).onchange_product_id()
		if self.product_id and (self.assembly_component_id or self.assembly_finished_id):
			self.price_unit = self.product_id.standard_price

	@api.onchange('product_uom_qty')
	def _onchange_product_uom_qty(self):
		super(StockMove, self)._onchange_product_uom_qty()
		if self.assembly_component_id and self.has_tracking == 'none':
			ko = self.assembly_component_id
			self._update_assembly_quantity_done(ko)

	def unlink(self):
		# Avoid deleting move related to active KO
		for move in self:
			if move.assembly_finished_id and move.assembly_finished_id.state != 'draft':
				raise ValidationError(_('Please cancel the Assembly Order first.'))
		return super(StockMove, self).unlink()

	def _action_assign(self):
		res = super(StockMove, self)._action_assign()
		for move in self.filtered(lambda x: x.assembly_finished_id or x.assembly_component_id):
			if move.move_line_ids:
				move.move_line_ids.write({'assembly_id': move.assembly_component_id.id})
		return res

	def action_explode(self):
		""" Explodes pickings """
		# in order to explode a move, we must have a picking_type_id on that move because otherwise the move
		# won't be assigned to a picking and it would be weird to explode a move into several if they aren't
		# all grouped in the same picking.
		moves_ids_to_return = OrderedSet()
		moves_ids_to_unlink = OrderedSet()
		phantom_moves_vals_list = []
		for move in self:
			if not move.picking_type_id or (move.production_id and move.production_id.product_id == move.product_id) or (move.assembly_finished_id and move.assembly_finished_id.product_id == move.product_id):
				moves_ids_to_return.add(move.id)
				continue
			bom = self.env['mrp.bom'].sudo()._bom_find(product=move.product_id, company_id=move.company_id.id, bom_type='phantom')
			if not bom:
				moves_ids_to_return.add(move.id)
				continue
			if move.picking_id.immediate_transfer:
				factor = move.product_uom._compute_quantity(move.quantity_done, bom.product_uom_id) / bom.product_qty
			else:
				factor = move.product_uom._compute_quantity(move.product_uom_qty, bom.product_uom_id) / bom.product_qty
			boms, lines = bom.sudo().explode(move.product_id, factor, picking_type=bom.picking_type_id)
			for bom_line, line_data in lines:
				if move.picking_id.immediate_transfer:
					phantom_moves_vals_list += move._generate_move_phantom(bom_line, 0, line_data['qty'])
				else:
					phantom_moves_vals_list += move._generate_move_phantom(bom_line, line_data['qty'], 0)
			# delete the move with original product which is not relevant anymore
			moves_ids_to_unlink.add(move.id)

		self.env['stock.move'].browse(moves_ids_to_unlink).sudo().unlink()
		if phantom_moves_vals_list:
			phantom_moves = self.env['stock.move'].create(phantom_moves_vals_list)
			phantom_moves._adjust_procure_method()
			moves_ids_to_return |= phantom_moves.action_explode().ids
		return self.env['stock.move'].browse(moves_ids_to_return)

	def _should_be_assigned(self):
		res = super(StockMove, self)._should_be_assigned()
		return bool(res and not (self.assembly_finished_id or self.assembly_component_id))

	def _should_bypass_reservation(self):
		res = super(StockMove, self)._should_bypass_reservation()
		return bool(res and not self.assembly_finished_id)

	def _key_assign_picking(self):
		keys = super(StockMove, self)._key_assign_picking()
		return keys + (self.created_assembly_id,)

	@api.model
	def _prepare_merge_moves_distinct_fields(self):
		distinct_fields = super()._prepare_merge_moves_distinct_fields()
		distinct_fields.append('created_assembly_id')
		return distinct_fields

	@api.model
	def _prepare_merge_move_sort_method(self, move):
		keys_sorted = super()._prepare_merge_move_sort_method(move)
		keys_sorted.append(move.created_assembly_id.id)
		return keys_sorted

	def _show_details_in_draft(self):
		self.ensure_one()
		production = self.assembly_component_id or self.assembly_finished_id
		if production and (self.state != 'draft' or production.state != 'draft'):
			return True
		elif production:
			return False
		else:
			return super()._show_details_in_draft()

	def _update_assembly_quantity_done(self, ko):
		self.ensure_one()
		new_qty = ko.product_uom_id._compute_quantity((ko.product_qty + ko.rejected_qty) * self.assembly_unit_factor, ko.product_uom_id, rounding_method='HALF-UP')
		if not self.is_quantity_done_editable:
			self.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).qty_done = 0
			self.move_line_ids = self._set_quantity_done_prepare_vals(new_qty)
		else:
			self.quantity_done = new_qty

	def _account_entry_move(self, qty, description, svl_id, cost):
		if self.assembly_component_id or self.assembly_finished_id:
			# create assembly moves from assembly model instead
			return False
		return super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)

	@api.onchange('assembly_quantity_done', 'assembly_component_id')
	def _onchange_assembly_quantity_done(self):
		if not self.assembly_component_id:
			return
		self.quantity_done = self.assembly_quantity_done


class StockMoveLine(models.Model):
	_inherit = 'stock.move.line'

	disassembly_qty = fields.Float()
