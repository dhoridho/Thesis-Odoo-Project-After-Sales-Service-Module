# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import time
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning

class PurchaseOrder(models.Model):
	_inherit = "purchase.order"

	merged = fields.Boolean(string='Merged')

	@api.depends('order_line.move_ids')
	def _compute_picking(self):
		for order in self:
			pickings = self.env['stock.picking']
			for line in order.order_line:
				# We keep a limited scope on purpose. Ideally, we should also use move_orig_ids and
				# do some recursive search, but that could be prohibitive if not done correctly.
				moves = line.move_ids | line.move_ids.mapped('returned_move_ids')
				moves = moves.filtered(lambda r: r.state != 'cancel')
				pickings |= moves.mapped('picking_id')
			order.picking_ids = pickings
		for order in self:
			if order.merged:
				for a in self.env['stock.picking'].search([]):
					if a.purchase_ids:
						for b in a.purchase_ids:
							if order.id == b.id:
								order.picking_ids = [(4, a.id)]
		for order in self:
			order.picking_count = len(order.picking_ids)



			
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
