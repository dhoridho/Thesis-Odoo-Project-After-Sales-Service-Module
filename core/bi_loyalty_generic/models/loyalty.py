# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _, tools
from datetime import date, time, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError,Warning
import logging
import math
_logger = logging.getLogger(__name__)


class res_partner(models.Model):
	_inherit = 'res.partner'

	loyalty_points = fields.Integer(string='Loyalty Points',compute='_compute_loyalty_points',store=True)
	loyalty_amount = fields.Float('Loyalty Amount')
	loyalty_history_ids = fields.One2many('all.loyalty.history','partner_id',string='Loyalty history')

	@api.depends('loyalty_history_ids','loyalty_history_ids.state','loyalty_history_ids.points','loyalty_history_ids.transaction_type')
	def _compute_loyalty_points(self):
		for rec in self:
			rec.loyalty_points = 0
			for history in rec.loyalty_history_ids :
				if history.state == 'done' and  history.transaction_type == 'credit' :
					rec.loyalty_points += history.points
				if history.state == 'done' and  history.transaction_type == 'debit' :
					rec.loyalty_points -= history.points

	def action_view_loyalty_points(self):
		self.ensure_one()

		partner_loyalty_ids = self.env['all.loyalty.history'].search([('partner_id','=',self.id)])

		return {
			'name': 'Loyalty Details',
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_model': 'all.loyalty.history',
			'domain': [('partner_id', '=', self.id)],
		}

	
class all_loyalty_setting(models.Model):
	_name = 'all.loyalty.setting'
	_description = 'all loyalty setting'
		
	name  = fields.Char('Name' ,default='Configuration for Loyalty Management')
	product_id  = fields.Many2one('product.product','Product', domain = [('type', '=', 'service'),('available_in_pos','=',True)],required=True)
	issue_date  =  fields.Date(default=fields.date.today(),required=True)
	expiry_date  = fields.Date('Expiry date',required=True)
	loyalty_basis_on = fields.Selection([('amount', 'Purchase Amount'), ('loyalty_category', 'Product Categories')], string='Loyalty Basis On',required=True)
	active  =  fields.Boolean('Active')
	loyality_amount = fields.Integer('Amount')
	amount_footer = fields.Integer('Footer Amount', related='loyality_amount')
	redeem_ids = fields.One2many('all.redeem.rule', 'loyality_id', 'Redemption Rule')

	@api.constrains('issue_date','expiry_date','active')
	def check_date(self):
		if self.expiry_date < self.issue_date :
			msg = _("Expiry Date should not be smaller than Issue Date. please change dates.")
			raise ValidationError(msg)
		flag = False
		for record in self.search([]):
			if record.active  and self.id != record.id:
				if (record.issue_date <= self.issue_date <=record.expiry_date) or (record.issue_date <= self.expiry_date <=record.expiry_date) : 
					flag = True
				if record.issue_date >= self.issue_date <=record.expiry_date : 
					flag = True
		if flag:
			msg = _("You can not apply two Loyalty Configuration within same date range please change dates.")
			raise ValidationError(msg)
	
	@api.model
	def search_loyalty_product(self,product_id):
		
		product = self.product_id.search([('id','=',product_id)])
		return product.id


class web_redeem_rule(models.Model):
	_name = 'all.redeem.rule' 
	_description = 'all redeem rule'   
	
	name = fields.Char('Name' ,default='Configuration for Website Redemption Management')
	min_amt = fields.Integer('Minimum Points')
	max_amt = fields.Integer('Maximum Points')
	reward_amt = fields.Integer('Redemption Amount')
	loyality_id = fields.Many2one('all.loyalty.setting', 'Loyalty ID')

	@api.onchange('max_amt','min_amt')
	def _check_amt(self):
		if (self.max_amt !=0):
			if(self.min_amt > self.max_amt):
				msg = _("Minimum Point is not larger than Maximum Point")
				raise ValidationError(msg)
		return

	@api.onchange('reward_amt')
	def _check_reward_amt(self):
		if self.reward_amt !=0:
			if self.reward_amt <= 0:			
				msg = _("Reward amount is not a zero or less than zero")
				raise ValidationError(msg)
		return

	@api.constrains('min_amt','max_amt')
	def _check_points(self):
		for line in self:
			record = self.env['all.redeem.rule'].search([('loyality_id','=',line.loyality_id.id)])
			for rec in record :
				if line.id != rec.id:
					if (rec.min_amt <= line.min_amt  <= rec.max_amt) or (rec.min_amt <=line.max_amt  <= rec.max_amt):
						msg = _("You can not create Redemption Rule with same points range.")
						raise ValidationError(msg)
						return


class web_loyalty_history(models.Model):
	_name = 'all.loyalty.history'
	_rec_name = 'partner_id'
	_order = 'id desc'
	_description = 'all loyalty history'  

	def _compute_check_state(self):
		for rec in self:
			rec.check_state = False
			if not rec.state :
				if rec.order_id and rec.order_id.state in ['sale','done'] :
					rec.state = 'done'
				elif rec.pos_order_id :
					rec.state = 'done'
				else:
					rec.state = 'draft' 
		
	order_id  = fields.Many2one('sale.order','Sale Order')
	pos_order_id  = fields.Many2one('pos.order','POS Order')
	partner_id  = fields.Many2one('res.partner','Customer')
	date  =  fields.Datetime(default = datetime.now())
	generated_from = fields.Selection([('sale', 'Sale'), ('pos', 'POS'),('website','Website')], string='Generated From')
	transaction_type = fields.Selection([('credit', 'Credit'), ('debit', 'Debit')], string='Transaction Type')
	points = fields.Integer('Loyalty Points')
	amount = fields.Char('Amount')
	currency_id = fields.Many2one('res.currency', 'Currency')
	company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
	
	check_state = fields.Boolean(compute='_compute_check_state')
	state = fields.Selection([('draft','Draft'),('done','Confirmed'),
		('cancel','Cancelled')],string="State",default='draft',readonly=True, copy=False)



		
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:    
