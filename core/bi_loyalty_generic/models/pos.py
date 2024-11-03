# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _, tools
from datetime import date, time, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError,Warning
import logging
_logger = logging.getLogger(__name__)


class pos_category(models.Model):
	_inherit = 'pos.category'
		
	Minimum_amount  = fields.Integer("Amount For loyalty Points")
	amount_footer = fields.Integer('Amount', related='Minimum_amount')

class pos_order(models.Model):
	_inherit = 'pos.order'

	@api.model
	def create_from_ui(self, orders, draft=False):
		order_ids = super(pos_order, self).create_from_ui(orders, draft=False)
		loyalty_history_obj = self.env['all.loyalty.history']
		today_date = datetime.today().date() 
		loyalty_setting = self.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
							('expiry_date', '>=', today_date )])
		if loyalty_setting:
			for order_id in order_ids:
				try:
					pos_order_id = self.browse(order_id.get('id'))
					if pos_order_id:
						ref_order = [o['data'] for o in orders if o['data'].get('name') == pos_order_id.pos_reference]
						for order in ref_order:
							cust_loyalty = pos_order_id.partner_id.loyalty_points + order.get('loyalty')
							order_loyalty = order.get('loyalty')
							redeemed = order.get('redeemed_points')

							if order_loyalty > 0:
								vals = {
									'pos_order_id':pos_order_id.id,
									'partner_id': pos_order_id.partner_id.id,
									'date' : datetime.now(),
									'transaction_type' : 'credit',
									'generated_from' : 'pos',
									'points': order_loyalty,
									'state': 'done',
								}
								loyalty_history = loyalty_history_obj.create(vals)	
														
							if order.get('redeem_done') == True:
								vals = {
									'pos_order_id':pos_order_id.id,
									'partner_id': pos_order_id.partner_id.id,
									'date' : datetime.now(),
									'transaction_type' : 'debit',
									'generated_from' : 'pos',
									'points': redeemed,
									'state': 'done',
								}
								loyalty_history = loyalty_history_obj.create(vals)
						
				except Exception as e:
					_logger.error('Error in point of sale validation: %s', tools.ustr(e))
			
		return order_ids

		
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:    
