# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, pycompat


class StockMoveLine(models.Model):

	_inherit = 'stock.move'

	# def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, description):
	# 	"""
	# 	Generate the account.move.line values to post to track the stock valuation difference due to the
	# 	processing of the given quant.
	# 	"""
	# 	self.ensure_one()

	# 	# the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
	# 	# the company currency... so we need to use round() before creating the accounting entries.
	# 	debit_value = self.company_id.currency_id.round(cost)
	# 	if self.product_id.cost_method == 'standard' and self.price_unit > 0.00:
	# 		value = self.price_unit * self.product_uom_qty
	# 		debit_value = self.company_id.currency_id.round(value)
	# 	elif self.product_id.cost_method == 'fifo' and self.price_unit > 0.00:
	# 		value = self.price_unit * self.product_uom_qty
	# 		debit_value = self.company_id.currency_id.round(value)
	# 	elif self.product_id.cost_method == 'average' and self.price_unit > 0.00:
	# 		value = self.price_unit * self.product_uom_qty
	# 		debit_value = self.company_id.currency_id.round(value)

	# 	credit_value = debit_value

	# 	valuation_partner_id = self._get_partner_id_for_valuation_lines()
	# 	res = [(0, 0, line_vals) for line_vals in self._generate_valuation_lines_data(valuation_partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description).values()]

	# 	return res



	def _run_valuation(self, quantity=None):
		self.ensure_one()
		value_to_return = 0
		if self._is_in():
			valued_move_lines = self.move_line_ids.filtered(lambda ml: not ml.location_id._should_be_valued() and ml.location_dest_id._should_be_valued() and not ml.owner_id)
			valued_quantity = 0
			for valued_move_line in valued_move_lines:
				valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, self.product_id.uom_id)
			# Note: we always compute the fifo `remaining_value` and `remaining_qty` fields no
			# matter which cost method is set, to ease the switching of cost method.
			vals = {}
			price_unit = self._get_price_unit()
			value = price_unit * (quantity or valued_quantity)
			value_to_return = value if quantity is None or not self.value else self.value
			if self.price_unit <= 0.00:
				self.write({
					'price_unit': price_unit,
					'value': value_to_return,
					'remaining_value': value if quantity is None else self.remaining_value + value,
				})
			else:
				self.write({
					'price_unit':self.price_unit,
					'value': value_to_return,
					'remaining_value': value if quantity is None else self.remaining_value + value,
				})
			vals['remaining_qty'] = valued_quantity if quantity is None else self.remaining_qty + quantity
			if self.product_id.cost_method == 'standard':
				value = self.product_id.standard_price * (quantity or valued_quantity)
				value_to_return = value if quantity is None or not self.value else self.value
				if self.price_unit <= 0.00:
					self.write({
						'price_unit': self.product_id.standard_price,
						'value': value_to_return,
					})
				else:
					self.write({
						'price_unit': self.price_unit,
						'value': value_to_return,
					})

		if self._is_out():
			valued_move_lines = self.move_line_ids.filtered(lambda ml: ml.location_id._should_be_valued() and not ml.location_dest_id._should_be_valued() and not ml.owner_id)
			valued_quantity = 0
			for valued_move_line in valued_move_lines:
				valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, self.product_id.uom_id)
			self.env['stock.move']._run_fifo(self, quantity=quantity)
			if self.product_id.cost_method in ['standard', 'average']:
				curr_rounding = self.company_id.currency_id.rounding
				value = -float_round(self.product_id.standard_price * (valued_quantity if quantity is None else quantity), precision_rounding=curr_rounding)
				value_to_return = value if quantity is None else self.value + value
				if self.price_unit <= 0.00:
					self.write({
						'value': value_to_return,
						'price_unit': value / valued_quantity,
					})
				else:
					self.write({
						'value': value_to_return,
						'price_unit': self.price_unit,
					})

		elif self._is_dropshipped() or self._is_dropshipped_returned():
			curr_rounding = self.company_id.currency_id.rounding
			if self.product_id.cost_method in ['fifo']:
				price_unit = self._get_price_unit()
				# see test_dropship_fifo_perpetual_anglosaxon_ordered
				self.product_id.standard_price = price_unit
			else:
				price_unit = self.product_id.standard_price
			value = float_round(self.product_qty * price_unit, precision_rounding=curr_rounding)
			value_to_return = value if self._is_dropshipped() else -value
			# In move have a positive value, out move have a negative value, let's arbitrary say
			# dropship are positive.
			if self.price_unit <= 0.00:
				self.write({
					'value': value_to_return,
					'price_unit': price_unit if self._is_dropshipped() else -price_unit,
				})
			else:
				self.write({
					'value': value_to_return,
					'price_unit':self.price_unit ,
				})
		return value_to_return

