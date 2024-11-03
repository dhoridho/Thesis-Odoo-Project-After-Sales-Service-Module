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


	def check_sync_order(self, vals):
		notsync_order_uids = vals['order_uids']
		values = { 'sync_order_uids': [], 'notsync_order_uids': [], }
		if notsync_order_uids:
			query = '''
				SELECT v.*
				FROM (values {_values}) v(pos_reference) 
				WHERE exists (
					SELECT 1 FROM pos_order po 
					WHERE po.pos_reference = v.pos_reference::CHARACTER VARYING
				);
			'''.format(_values=','.join([ f"('{x}')" for x in notsync_order_uids]))
			self._cr.execute(query)
			sync_order_uids = [x[0] for x in self._cr.fetchall()]
			notsync_order_uids = [x for x in notsync_order_uids if x not in sync_order_uids]
			values['sync_order_uids'] = sync_order_uids
			values['notsync_order_uids'] = notsync_order_uids

		return values

class PosOrderLine(models.Model):
	_inherit = 'pos.order.line'

	is_product_exchange = fields.Float('Line Product Exchange')
	product_exchange_price = fields.Float('Line Product Exchange Price')
	is_fee_of_product_exchange = fields.Boolean('Fee of Product Exchange')