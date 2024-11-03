# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, pycompat


class InventoryLine(models.Model):
	_inherit = 'stock.inventory.line'

	currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
	unit_price = fields.Monetary(readonly=False)
	inv_cost = fields.Boolean(default=False, related="company_id.inv_cost")


	@api.onchange('product_id', 'location_id', 'product_uom_id', 'prod_lot_id', 'partner_id', 'package_id')
	def _onchange_quantity_context(self):
		res = super(InventoryLine,self)._onchange_quantity_context()
		product_qty = False
		if self.product_id:
			self.product_uom_id = self.product_id.uom_id
			self.unit_price = self.product_id.standard_price
		if self.product_id and self.location_id and self.product_id.uom_id.category_id == self.product_uom_id.category_id:  # TDE FIXME: last part added because crash
			theoretical_qty = self.product_id.get_theoretical_quantity(
				self.product_id.id,
				self.location_id.id,
				lot_id=self.prod_lot_id.id,
				package_id=self.package_id.id,
				owner_id=self.partner_id.id,
				to_uom=self.product_uom_id.id,
			)
		else:
			theoretical_qty = 0
		# Sanity check on the lot.
		if self.prod_lot_id:
			if self.product_id.tracking == 'none' or self.product_id != self.prod_lot_id.product_id:
				self.prod_lot_id = False

		if self.prod_lot_id and self.product_id.tracking == 'serial':
			# We force `product_qty` to 1 for SN tracked product because it's
			# the only relevant value aside 0 for this kind of product.
			self.product_qty = 1
		elif self.product_id and float_compare(self.product_qty, self.theoretical_qty, precision_rounding=self.product_uom_id.rounding) == 0:
			# We update `product_qty` only if it equals to `theoretical_qty` to
			# avoid to reset quantity when user manually set it.
			self.product_qty = theoretical_qty
		self.theoretical_qty = theoretical_qty
		return res
		
	@api.model
	def default_get(self,fields):
		res = super(InventoryLine, self).default_get(fields)

		if 'unit_price' in fields and res.get('product_id'):
			res['unit_price'] = self.env['product.product'].browse(res['product_id']).standard_price
		return res

	def _get_move_values(self, qty, location_id, location_dest_id, out):
		self.ensure_one()
		res = super(InventoryLine,self)._get_move_values(qty, location_id, location_dest_id, out)
		res.update({
			'price_unit':self.unit_price
			})
		return res

