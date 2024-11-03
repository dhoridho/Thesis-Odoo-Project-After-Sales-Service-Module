# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import json
import werkzeug
import odoo
from odoo import addons
from odoo import models, fields, api
from odoo import SUPERUSER_ID
from odoo import http, tools, _
from odoo.http import request
from odoo.tools.translate import _
import odoo.http as http
from odoo.http import request
from datetime import datetime, timedelta
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager

import werkzeug.urls
import werkzeug.wrappers
from odoo.addons.website_sale.controllers.main import WebsiteSale
	

class WebsiteSaleInherit(WebsiteSale):

	@http.route(['/get-loyalty-points'], type='http', auth='public', website=True)
	def get_loyalty_points(self , **post):
		so = request.env['sale.order'].sudo().browse(int(post.get('order_id')))
		today_date = datetime.today().date() 
		config = request.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
							('expiry_date', '>=', today_date )])
		redeem_value = 0.0
		loyalty_amount = 0.0
		partner = so.partner_id
		company_currency = request.website.company_id.currency_id
		web_currency = request.website.get_current_pricelist().currency_id
		if so:
			for rule in config.redeem_ids:
				if rule.min_amt <= partner.loyalty_points  and   partner.loyalty_points <= rule.max_amt :
					redeem_value = rule.reward_amt

			if company_currency.id != web_currency.id:
				new_redeem = (redeem_value*web_currency.rate)/company_currency.rate
				redeem_value = round(new_redeem,2)
			
			loyalty_amount = round(redeem_value * partner.loyalty_points ,2)

			data ={
				'partner' : partner.name,
				'points' : partner.loyalty_points,
				'loyalty_amount' : loyalty_amount,
				'redeem_value' : redeem_value,
				'amount_total' : so.amount_total,
				'order_redeem_points' : so.order_redeem_points
			}
			return json.dumps(data)

	@http.route(['/redeem-loyalty-points'], type='http', auth='public', website=True)
	def redeem_loyalty_points(self , **post):
		so = request.env['sale.order'].sudo().browse(int(post.get('order_id')))
		today_date = datetime.today().date() 
		config = request.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
							('expiry_date', '>=', today_date )])
		partner = so.partner_id
		if config:
			res = request.env['sale.order.line'].sudo().create({
				'product_id': config.product_id.id,
				'name': config.product_id.name,
				'price_unit': -int(post.get('entered_points')) * float(post.get('redeem_value')),
				'order_id': so.id,
				'product_uom':config.product_id.uom_id.id,
				'discount_line':True,
				'redeem_points' : int(post.get('entered_points'))
			})
			so.sudo().write({
				'order_redeem_points' :  int(post.get('entered_points')) ,
				'redeem_value' : float(post.get('redeem_value')),
			})
			return json.dumps(res.id)


	@http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
	def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True):
		"""This route is called when changing quantity from the cart or adding
		a product from the wishlist."""
		order = request.website.sale_get_order()
		order.write({'is_from_website': True})
		so_line = request.env['sale.order.line'].sudo().browse(line_id)
		if so_line.discount_line and set_qty == 0:
			partner = so_line.order_id.partner_id
			so_line.order_id.sudo().write({
				'order_redeem_points' :  0
			})
		return super(WebsiteSaleInherit, self).cart_update_json(product_id, line_id,add_qty,set_qty,display)


class PortalLoyaltyHistory(CustomerPortal):

	
	def _prepare_portal_layout_values(self):
		values = super(PortalLoyaltyHistory, self)._prepare_portal_layout_values()
		partner = request.env.user.partner_id
		LoyaltyHistory = request.env['all.loyalty.history'].sudo()
		loyalty_count = LoyaltyHistory.sudo().search_count([
			('partner_id', '=', partner.id)])
		values.update({
			'loyalty_count': loyalty_count,
		})
		return values	
	
	@http.route(['/my/loyalty/history', '/my/quotes/page/<int:page>'], type='http', auth="user", website=True)
	def portal_my_wallet_transaction(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
		
		values = self._prepare_portal_layout_values()
		partner = request.env.user.partner_id
		LoyaltyHistory = request.env['all.loyalty.history'].sudo()
		domain = [('partner_id', '=', partner.id)]
			
		searchbar_sortings = {
			'id': {'label': _('Loyalty History'), 'order': 'id desc'},
			
		}
		if not sortby:
			sortby = 'id'
		sort_loyalty = searchbar_sortings[sortby]['order']
		# count for pager
		loyalty_count = LoyaltyHistory.sudo().search_count(domain)
		# make pager
		pager = portal_pager(
			url="/my/loyalty/history",
			total=loyalty_count,
			page=page,
			step=self._items_per_page
		)
		loyalty_points = LoyaltyHistory.sudo().search(domain, order=sort_loyalty, limit=self._items_per_page, offset=pager['offset'])
		values.update({
			'loyalty_points': loyalty_points.sudo(),
			'page_name': 'loyalty_points',
			'pager': pager,
			'default_url': '/my/loyalty/history',
		})
		return request.render("bi_loyalty_generic.portal_loyalty_history", values)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
