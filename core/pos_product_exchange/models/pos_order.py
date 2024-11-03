# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PosOrder(models.Model):
	_inherit = 'pos.order'

	exchange_amount = fields.Float('Exchange Amount')
	is_exchange_order = fields.Boolean('Exchange Order')

	@api.model
	def _order_fields(self, ui_order):
		res = super(PosOrder,self)._order_fields(ui_order)
		res.update({
			'is_exchange_order': ui_order.get('is_exchange_order') or False,
			'exchange_amount': ui_order.get('exchange_amount') or False,
		})
		return res

class PosOrderLine(models.Model):
	_inherit = 'pos.order.line'

	is_product_exchange = fields.Float('Line Product Exchange')
	product_exchange_price = fields.Float('Line Product Exchange Price')
	is_fee_of_product_exchange = fields.Boolean('Fee of Product Exchange')


