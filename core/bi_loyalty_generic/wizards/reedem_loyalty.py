# -*- coding: utf-8 -*-

from odoo import models, fields, api, _,tools
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError,Warning
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging
_logger = logging.getLogger(__name__)

	
class ReedemptionLoyalty(models.TransientModel):
	_name = 'loyalty.wizard.reedem'
	_description = "Loyalty Redeem Wizard "

	order_credit_points = fields.Integer(string='Order Credit Points',copy=False)
	order_redeem_points = fields.Integer(string='Order Redeemed Points',copy=False)
	redeem_point=fields.Integer("Reedemption Loyalty Point",copy=False)
	customer=fields.Char(string="Customer Name:",readonly=True,copy=False)
	loyalty_point=fields.Float(string="Your Loyalty Points (in point(s)):",readonly=True,copy=False)
	loyalty_balance=fields.Float(string="Your Loyalty Balance:",readonly=True,copy=False)

	@api.model
	def default_get(self, fields):  
		rec = super(ReedemptionLoyalty, self).default_get(fields)  
		active_ids = self._context.get('active_ids')
		result=self.env['sale.order'].browse(active_ids)
		if result:	
			today_date = datetime.today().date() 
			amt_total = result.amount_total
			partner_id =result.partner_id
			loyalty_points = 0.0
			plus_points = 0.0
			redeem_value=0.0
			total_loyalty = 0.0
			config = self.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
								('expiry_date', '>=', today_date )])		
			
			for rule in config.redeem_ids:
				if rule.min_amt <= partner_id.loyalty_points and partner_id.loyalty_points <= rule.max_amt :
					redeem_value = rule.reward_amt
			loyalty_balance = round(redeem_value * partner_id.loyalty_points ,2)
			
			rec.update({'customer':partner_id.name,
				'loyalty_point':partner_id.loyalty_points,
				'loyalty_balance':loyalty_balance,       
			})
						
		return rec
	
	def ok_redeem(self):
		active_ids = self._context.get('active_ids')
		redeem_value=0.0		
		today_date = datetime.today().date()		
		result=self.env['sale.order'].browse(active_ids)
		partner_id =result.partner_id

		if self.redeem_point <= 0 :
			raise ValidationError(_('Please enter valid loyalty points'))				

		config = self.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
							('expiry_date', '>=', today_date )])		
		if self.redeem_point > partner_id.loyalty_points or self.redeem_point < 0:
			raise ValidationError(_('You can not redeem more than loyalty points'))				
		today_date = datetime.today().date()	
		is_exist= None
		if config:	
			point_amt = 0
			for rule in config.redeem_ids:
				if rule.min_amt <= partner_id.loyalty_points  and   partner_id.loyalty_points <= rule.max_amt :
					redeem_value = rule.reward_amt
					point_amt+=int(self.redeem_point) * redeem_value
			loyalty_balance = round(redeem_value * partner_id.loyalty_points ,2)			
			if point_amt > result.amount_total:
				raise ValidationError(_('You can not redeem more than total amount'))							
			for line in result.order_line:				
				if config.product_id.id == line.product_id.id:					
					is_exist=line
					break				
			if not is_exist:
				self.env['sale.order.line'].sudo().create({
						'product_id': config.product_id.id,
						'name': config.product_id.name,
						'price_unit': -point_amt,
						'order_id': result.id,
						'product_uom':config.product_id.uom_id.id,
						'discount_line':True,
						'redeem_points' : int(self.redeem_point)
					})		
				result.update({			
					'order_redeem_points':self.redeem_point,
					'redeem_value' : point_amt,
				})
			else:	
				raise ValidationError(_('You can not redeem more than one time'))			
		
		return


class SaleInherit(models.Model):

	_inherit = "sale.order"

	loyalty_point_credit=fields.Float(string="Your Loyalty Balance:",readonly=True,copy=False)
	
	def action_confirm(self):		
		res = super(SaleInherit,self).action_confirm()
		loyalty_history_obj = self.env['all.loyalty.history']	
		today_date = datetime.today().date()
		config = self.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
								('expiry_date', '>=', today_date )])
		if config : 
			for rec in self:
				partner_id =rec.partner_id
				plus_points = 0.0

				company_currency = rec.company_id.currency_id
				web_currency = rec.pricelist_id.currency_id		
				
				if config.loyalty_basis_on == 'amount' :
					if config.loyality_amount > 0 :
						price = sum(rec.order_line.filtered(lambda x: not x.is_delivery).mapped('price_total'))	
						if company_currency.id != web_currency.id:
							new_rate = (price*company_currency.rate)/web_currency.rate
						else:
							new_rate = price
						plus_points =  int( new_rate / config.loyality_amount)

				if config.loyalty_basis_on == 'loyalty_category' :
					for line in  rec.order_line:
						if not line.discount_line or not line.is_delivery :
							if rec.is_from_website :
								prod_categs = line.product_id.public_categ_ids
								for c in prod_categs :
									if c.Minimum_amount > 0 :
										if company_currency.id != web_currency.id:
											price = line.price_total
											new_rate = (price*company_currency.rate)/web_currency.rate
										else:
											new_rate = line.price_total
										plus_points += int(new_rate / c.Minimum_amount)
							else:
								prod_categ = line.product_id.categ_id
								if prod_categ.Minimum_amount > 0 :
									if company_currency.id != web_currency.id:
										price = line.price_total
										new_rate = (price*company_currency.rate)/web_currency.rate
									else:
										new_rate = line.price_total
									plus_points += int(new_rate / prod_categ.Minimum_amount)
				
				if rec.order_redeem_points > 0:
					is_debit = loyalty_history_obj.search([('order_id','=',rec.id),('transaction_type','=','debit')])
					if is_debit:
						is_debit.write({
							'points': rec.order_redeem_points,
							'state': 'done',
							'date' : datetime.now(),
							'partner_id': partner_id.id,
						})
					else:
						vals = {
							'order_id':rec.id,
							'partner_id': partner_id.id,
							'date' : datetime.now(),
							'transaction_type' : 'debit',
							'generated_from' : 'sale',
							'points': rec.order_redeem_points,
							'state': 'done',
						}
						loyalty_history = loyalty_history_obj.sudo().create(vals)
				
				if plus_points > 0 :
					is_credit = loyalty_history_obj.search([('order_id','=',rec.id),('transaction_type','=','credit')])
					if is_credit:
						is_credit.write({
							'points': plus_points,
							'state': 'done',
							'date' : datetime.now(),
							'partner_id': partner_id.id,
						})
					else:
						vals = {
							'order_id':rec.id,
							'partner_id': partner_id.id,
							'date' : datetime.now(),
							'transaction_type' : 'credit',
							'generated_from' : 'sale',
							'points': plus_points,
							'state': 'done',
						}
						loyalty_history = loyalty_history_obj.sudo().create(vals)
					rec.write({'order_credit_points':plus_points})
		return res
	
	def action_cancel(self):		
		res = super(SaleInherit,self).action_cancel()
		loyalty_history_obj = self.env['all.loyalty.history']	
		for rec in self:
			loyalty = loyalty_history_obj.search([('order_id','=',rec.id)])
			for l in loyalty:
				l.write({
					'state' : 'cancel'
				})
		return res
