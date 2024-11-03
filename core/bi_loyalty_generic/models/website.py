# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _, tools
from datetime import date, time, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError,Warning
import logging
import math
from odoo.http import request

_logger = logging.getLogger(__name__)
	

class web_category(models.Model):
	_inherit = 'product.public.category'

	Minimum_amount  = fields.Integer("Amount For loyalty Points")
	amount_footer = fields.Integer('Amount', related='Minimum_amount')


class ProviderGrid(models.Model):
	_inherit = 'delivery.carrier'

	def _get_price_available(self, order):
		self.ensure_one()
		self = self.sudo()
		order = order.sudo()
		total = weight = volume = quantity = 0
		total_delivery = 0.0
		for line in order.order_line:
			if not line.discount_line :
				if line.state == 'cancel':
					continue
				if line.is_delivery:
					total_delivery += line.price_total
				if not line.product_id or line.is_delivery:
					continue
				qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
				weight += (line.product_id.weight or 0.0) * qty
				volume += (line.product_id.volume or 0.0) * qty
				quantity += qty
		total = (order.amount_total or 0.0) - total_delivery

		total = order.currency_id._convert(
			total, order.company_id.currency_id, order.company_id, order.date_order or fields.Date.today())

		return self._get_price_from_picking(total, weight, volume, quantity)


class Website(models.Model):
	_inherit = 'website'
		
	def get_loyalty_balance(self,order): 
		today_date = datetime.today().date() 
		amt_total = order.amount_total
		partner_id =order.partner_id
		loyalty_points = 0.0
		plus_points = 0.0
		total_loyalty = 0.0
		company_currency = self.company_id.currency_id
		web_currency = self.get_current_pricelist().currency_id

		order.write({'is_from_website': True})

		config = self.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
							('expiry_date', '>=', today_date )])
		
		path = request.httprequest.full_path
		show_redeem = True
		
		if config : 
			if config.loyalty_basis_on == 'amount' :
				if config.loyality_amount > 0 :
					price = sum(order.order_line.filtered(lambda x: not x.is_delivery).mapped('price_total'))	
					if company_currency.id != web_currency.id:
						new_rate = (price*company_currency.rate)/web_currency.rate
					else:
						new_rate = price
					plus_points =  int( new_rate / config.loyality_amount )
					total_loyalty = partner_id.loyalty_points + plus_points

			if config.loyalty_basis_on == 'loyalty_category' :
				for line in  order.order_line:
					if not line.is_delivery :
						prod_categs = line.product_id.public_categ_ids
						for c in prod_categs :
							if c.Minimum_amount > 0 :
								if company_currency.id != web_currency.id:
									price = line.price_total
									new_rate = (price*company_currency.rate)/web_currency.rate
								else:
									new_rate = line.price_total
								plus_points += int(new_rate / c.Minimum_amount)

				total_loyalty = partner_id.loyalty_points + plus_points

			if "/shop/confirmation" in str(path) :
				total_loyalty = partner_id.loyalty_points 
				show_redeem = False

			total_loyalty -= order.order_redeem_points

		return [plus_points,total_loyalty,show_redeem]
			

		
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:    
