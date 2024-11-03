# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api,  models, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_round, float_is_zero

class Picking(models.Model):
	_inherit = 'stock.picking'

	def action_cancel_draft(self):
		# make sure this method only apply for rental pickings
		rental_pickings = self.rental_pickings()

		if not len(rental_pickings.ids):
			return False

		move_obj = self.env['stock.move']
		for (ids, name) in rental_pickings.name_get():
			message = _("Picking '%s' has been set in draft state.") % name
			rental_pickings.message_post(message)
		for pick in rental_pickings:
			ids2 = [move.id for move in pick.move_lines]
			moves = move_obj.browse(ids2)
			moves.sudo().action_draft()
		return True


class StockMove(models.Model):
	_inherit = 'stock.move'
	
	def action_cancel_quant_create(self):
		# make sure this method only apply for rental moves
		rental_moves = self.rental_moves()

		if not rental_moves:
			return

		quant_obj = self.env['stock.quant']
		for move in rental_moves:
			price_unit = move.get_price_unit()
			location = move.location_id
			rounding = move.product_id.uom_id.rounding
			vals = {
				'product_id': move.product_id.id,
				'location_id': location.id,
				'qty': float_round(move.product_uom_qty, precision_rounding=rounding),
				'cost': price_unit,
				'in_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
				'company_id': move.company_id.id,
			}
			quant_obj.sudo().create(vals)
		
	def action_draft(self):
		# make sure this method only apply for rental moves
		rental_moves = self.rental_moves()
		if not rental_moves:
			return
		return rental_moves.write({'state': 'draft'})
	
	# def _do_unreserve(self):
	# 	for move in self:
	# 		move.move_line_ids.unlink()
	# 		if move.procure_method == 'make_to_order' and not move.move_orig_ids:
	# 			move.state = 'waiting'
	# 		elif move.move_orig_ids and not all(orig.state in ('done', 'cancel') for orig in move.move_orig_ids):
	# 			move.state = 'waiting'
	# 		else:
	# 			move.state = 'confirmed'
	# 	return True

	# def _action_cancel(self):
	# 	for move in self:
	# 		move._do_unreserve()
	# 		siblings_states = (move.move_dest_ids.mapped('move_orig_ids') - move).mapped('state')
	# 		if move.propagate_cancel:
	# 			# only cancel the next move if all my siblings are also cancelled
	# 			if all(state == 'cancel' for state in siblings_states):
	# 				move.move_dest_ids._action_cancel()
	# 		else:
	# 			if all(state in ('done', 'cancel') for state in siblings_states):
	# 				move.move_dest_ids.write({'procure_method': 'make_to_stock'})
	# 				move.move_dest_ids.write({'move_orig_ids': [(3, move.id, 0)]})
		
	# 		if move.picking_id.state == 'done' or 'confirmed':
	# 			pack_op = self.env['stock.move'].sudo().search([('picking_id','=',move.picking_id.id),('product_id','=',move.product_id.id)])
	# 			#outgoing
	# 			for pack_op_id in pack_op:
	# 				if move.picking_id.picking_type_id.code in ['outgoing','internal']:
	# 					for move_id in pack_op:
	# 						for line in move_id.move_line_ids:
	# 							if line.lot_id:
	# 								lot_outgoing_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',line.location_dest_id.id),('lot_id','=',line.lot_id.id)])
	# 								lot_source_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',line.location_id.id),('lot_id','=',line.lot_id.id)])
	# 								if lot_outgoing_quant.product_id.tracking == 'lot'or lot_source_quant.product_id.tracking == 'lot':
	# 									if lot_outgoing_quant:
	# 										for lot in lot_outgoing_quant:
	# 											old_qty = lot.quantity
	# 											lot.quantity = old_qty - move.product_uom_qty
	# 									if lot_source_quant:
	# 										for lot in lot_source_quant:
	# 											old_qty = lot.quantity
	# 											lot.quantity = old_qty + move.product_uom_qty
	# 									else:
	# 										vals = { 'product_id' :move.product_id.id,
	# 												'location_id':move.location_id.id,
	# 												'lot_id':line.lot_id.id,
	# 												'quantity':move.product_uom_qty,
	# 											}
	# 										self.env['stock.quant'].create(vals)
	# 								else:
	# 									if lot_outgoing_quant:
	# 										for lot in lot_outgoing_quant:
	# 											old_qty = lot.quantity
	# 											lot.unlink()
	# 											vals = { 'product_id' :move.product_id.id,
	# 													'location_id':move.location_id.id,
	# 													'quantity': old_qty,
	# 													'lot_id':line.lot_id.id,
	# 												}
	# 											test = self.env['stock.quant'].create(vals)
											
	# 							else:
	# 								if pack_op_id.location_dest_id.usage == 'customer':
	# 									outgoing_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_dest_id.id)])
	# 									stock_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_id.id)])
	# 									if outgoing_quant:
	# 										old_qty = outgoing_quant[0].quantity
	# 										outgoing_quant[0].quantity = old_qty - move.product_uom_qty
	# 									if stock_quant:
	# 										old_qty = stock_quant[0].quantity
	# 										stock_quant[0].quantity = old_qty + move.product_uom_qty
	# 								else:
	# 									outgoing_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_id.id)])
	# 									if outgoing_quant:
	# 										old_qty = outgoing_quant[0].quantity
	# 										outgoing_quant[0].quantity = old_qty + move.product_uom_qty
	# 									outgoing_customer_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_dest_id.id)])
	# 									if outgoing_customer_quant:
	# 										old_qty = outgoing_quant[0].quantity
	# 										outgoing_quant[0].quantity = old_qty - move.product_uom_qty

	# 				if move.picking_id.picking_type_id.code == 'incoming':
	# 					incoming_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_dest_id.id)])
	# 					if incoming_quant:
	# 						old_qty = incoming_quant[0].quantity
	# 						incoming_quant[0].quantity = old_qty - move.product_uom_qty
	# 					incoming_customer_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_id.id)])
	# 					if incoming_customer_quant:
	# 						old_qty = incoming_customer_quant[0].quantity
	# 						incoming_customer_quant[0].quantity = old_qty + move.product_uom_qty
					
	# 		self.write({'state': 'cancel', 'move_orig_ids': [(5, 0, 0)]})        
	# 	return True

# class stock_move_line(models.Model):
# 	_inherit = "stock.move.line"
	
# 	def unlink(self):
# 		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
# 		for ml in self:
# 			# Unlinking a move line should unreserve.
# 			if ml.product_id.type == 'product' and not ml.location_id.should_bypass_reservation() and not float_is_zero(ml.product_qty, precision_digits=precision):

# 				quant = self.env['stock.quant']._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=ml.lot_id,
# 																   package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
# 		return 

			
