# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _, tools
from datetime import date, time, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError,Warning
import logging
import math

_logger = logging.getLogger(__name__)

class web_category(models.Model):
	_inherit = 'product.category'

	Minimum_amount  = fields.Integer("Amount For loyalty Points")
	amount_footer = fields.Integer('Amount', related='Minimum_amount')

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	order_credit_points = fields.Integer(string='Order Credit Points',copy=False)
	order_redeem_points = fields.Integer(string='Order Redeemed Points',copy=False)
	redeem_value = fields.Float(string='Redeem point value',copy=False)
	is_from_website = fields.Boolean("Is from Website",copy=False,readonly=True)

	def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
		res = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)
		if res.get('quantity') != 0 :
			self.ensure_one()
			OrderLine = self.env['sale.order.line']
			line = OrderLine.sudo().browse(line_id)
			if line and line.discount_line :
				line.write({
					'price_unit' : - line.redeem_points * line.order_id.redeem_value
				})
		return res
		

class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	discount_line = fields.Boolean(string='Discount line',readonly=True,copy=False)
	redeem_points = fields.Integer(string='Redeem Points',copy=False)
	redeem_value = fields.Float(string='Redeem point value',copy=False)
