# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, pycompat


class ProductIn(models.Model):
	_inherit = 'product.product'

	def _prepare_in_svl_vals(self, quantity, unit_cost):
		"""Prepare the values for a stock valuation layer created by a receipt.

		:param quantity: the quantity to value, expressed in `self.uom_id`
		:param unit_cost: the unit cost to value `quantity`
		:return: values to use in a call to create
		:rtype: dict
		"""
		self.ensure_one()
		if self.cost_method in ['standard']:
			for move in self.stock_move_ids:
				unit_cost = move.price_unit 

		vals = {
			'product_id': self.id,
			'value': unit_cost * quantity,
			'unit_cost': unit_cost,
			'quantity': quantity,
		}
		if self.cost_method in ('average', 'fifo'):
			vals['remaining_qty'] = quantity
			vals['remaining_value'] = vals['value']
		return vals

	def _prepare_out_svl_vals(self, quantity, company):
		"""Prepare the values for a stock valuation layer created by a delivery.

		:param quantity: the quantity to value, expressed in `self.uom_id`
		:return: values to use in a call to create
		:rtype: dict
		"""
		self.ensure_one()
		if self.cost_method in ['standard']:
			for move in self.stock_move_ids:
				unit_cost = move.price_unit 

		# Quantity is negative for out valuation layers.
		quantity = -1 * quantity
		vals = {
			'product_id' : self.id,
			'value': quantity * self.standard_price,
			'unit_cost': self.standard_price,
			'quantity': quantity,
		}
		if self.cost_method in ('average', 'fifo'):
			fifo_vals = self._run_fifo(abs(quantity), company)
			vals['remaining_qty'] = fifo_vals.get('remaining_qty')
			if self.cost_method == 'fifo':
				vals.update(fifo_vals)
		return vals
	