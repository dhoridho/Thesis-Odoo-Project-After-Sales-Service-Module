# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from dateutil import relativedelta

class ProductProduct(models.Model):
	_inherit = 'product.product'

	invoice_count = fields.Integer("#Invoice", compute='_compute_invoice_count')
	contract_count = fields.Integer("#Contract", compute='_compute_contract_count')
	maintain_count =  fields.Integer("#Maintain", compute='_compute_maintanance')
	is_property = fields.Boolean(string="Property")
	deposite = fields.Float("Monthly Rent")
	maintain_charge = fields.Float("Maintenance Charge")
	reasonable_price = fields.Boolean("Allow Discount(%)")
	owner_id = fields.Many2one('res.partner', string="Property Owner")
	user_id = fields.Many2one('res.users', string="Login User")
	salesperson_id = fields.Many2one('res.users', string="Salesperson",default=lambda self: self.env.user)
	facility_ids = fields.Many2many('property.facility', string="Facility & Services")
	property_book_for = fields.Selection([('sale','Sale'),('rent','Rent')], string=" Property Type", help="property reserve for rent and sale.")
	property_type = fields.Many2one('property.type')
	rent_price = fields.Float("Property Rent")
	reasonable_rent = fields.Boolean("Allow Discount in(%)")
	discounted_price = fields.Float("Reasonable Price")
	property_price = fields.Float()
	partial_payment_ids = fields.Many2many('partial.payment','property_partial_payment', string='Allow Partial Payment' )
	user_commission_ids = fields.One2many('user.commission', 'property_id', string="Commission" )
	renter_history_ids = fields.One2many('renter.history', 'property_id' ) 
	state = fields.Selection([('draft','Draft'),('rent','Rentable'),('sale','Saleable'),('reserve','Reserve'),('sold','Sold'),('cancel','Cancelled')], string="Property Status", track_visibility="onchange", help='State of the Propertsy')
	property_floor = fields.Integer()
	carpet_area = fields.Char("Carpet Area")
	build_area =fields.Char("Build-up Area")
	construction_status = fields.Char("Construction Status",default="Ready to Move")
	plot_area = fields.Char()
	invoice_ids = fields.Many2many('account.move', 'partial_payment_account_invoice')
	location = fields.Char("Address")
	city = fields.Char()
	street = fields.Char()
	zipcode = fields.Integer("Zip")
	state_id = fields.Many2one('res.country.state', string="State")
	country_id = fields.Many2one('res.country', string="Country")
	phone = fields.Char("Phone")
	bedrooms  = fields.Char()
	balconies = fields.Integer()
	washroom = fields.Integer()
	more_details = fields.Text("More Details")
	rent_unit = fields.Selection([('monthly','Monthly'),('yearly','Yearly')], default='monthly')
	property_avl_from = fields.Date("Property Exist From")
	is_partial = fields.Boolean()
	is_reserved = fields.Boolean()
	is_sold = fields.Boolean()
	age = fields.Integer('Property Age')
	months = fields.Integer('Months')
	reasonable_percent = fields.Float("Reasonable Rent Percentage")
	reasonable_price_per = fields.Float("Reasonable Price Percentage")
	variant_short_name = fields.Char(string='Variant Short Name', compute='_compute_variant_short_name')

	@api.depends('name', 'default_code')
	def _compute_variant_short_name(self):
		for product in self:
			product.variant_short_name = "%s%s" % (product.default_code, product.name)
	

	def unlink(self):
		for line in self:
			if line.state != 'draft':
				raise UserError(_('You cannot delete Sale And Rent Property (name: %s)') % (line.name,))
		return super(ProductProduct, self).unlink()

	@api.onchange('state_id')
	def get_country(self):
		if self.state_id:
			self.country_id = self.state_id.country_id

	@api.onchange('property_avl_from')
	def culculate_age(self):
		if self.property_avl_from:
			if self.property_avl_from > date.today():
				return {
						 'warning': {'title': 'Warning!', 'message': 'Please enter valid property exist date...!'},
						  'value': {'property_avl_from': None}
						}

			self.age = 0
			self.months = 0
			days_in_year = 365
			year = int((date.today() - self.property_avl_from).days / days_in_year)
			result = relativedelta.relativedelta(fields.Date.today(), self.property_avl_from)
			months = result.months + (12*result.years)
			if year > 0:
				self.age = year
			else:
				self.months = months

	def button_confirm(self):
		if self.state == 'draft' and self.property_book_for == 'sale':
			if self.property_price <= 0 or self.discounted_price <= 0:
				raise UserError(_("Please enter valid property price or reasonable amount...!"))
			self.state = 'sale'
		if self.state == 'draft' and self.property_book_for == 'rent':
			if self.rent_price <= 0 or self.deposite <= 0:
				raise UserError(_("Please enter valid property rent amount...!"))
			contracts = self.env['contract.contract'].search([])
			if not contracts:
				raise UserError(_("Please first create contract type from property configuration -> contract...!"))
			self.state = 'rent'

		if self.user_commission_ids:
			for each in self.user_commission_ids:
				if each.percentage <= 0:
					raise UserError(_("Please enter valid commission percentage in commission lines...!"))

	def button_set_to_draft(self):
		if self.state in ['rent','sale']:
			self.state = 'draft'

	@api.onchange('state')
	def change_state(self):
		if self.renter_history_ids or self.invoice_ids:
			raise UserError(_("You can not move this property(%s) in another state..!")%self.name)
		if self.state == 'sale':
			self.property_book_for = 'sale'
		elif self.state == 'rent':
			self.property_book_for = 'rent'

	@api.onchange('reasonable_percent','reasonable_rent','rent_price')
	def calculate_reasonable_rent(self):
		if self.reasonable_rent:
			if self.reasonable_percent > 0:
				discount = (self.rent_price * self.reasonable_percent)/100
				self.deposite = self.rent_price - discount
			else:
				self.deposite = self.rent_price
		else:
			self.deposite = self.rent_price

	@api.onchange('reasonable_price_per','reasonable_price','property_price')
	def calculate_reasonable_price(self):
		if self.reasonable_price:
			if self.reasonable_price_per > 0:
				discount  = (self.property_price * self.reasonable_price_per)/100
				self.discounted_price = self.property_price - discount
			else:
				self.discounted_price = self.property_price
		else:
			self.discounted_price = self.property_price

	@api.depends()
	def _compute_invoice_count(self):
		for rec in self:
			invoices = self.env['account.move'].search([('property_id','=',rec.id)])
			rec.invoice_count = len(invoices)

	@api.depends()
	def _compute_contract_count(self):
		for rec in self:
			contracts = self.env['contract.details'].search([('property_id','=',rec.id)])
			rec.contract_count = len(contracts)

	@api.depends()
	def _compute_maintanance(self):

		for rec in self:
			maintanance = self.env['property.maintanance'].search([('property_id','=',rec.id)])
			rec.maintain_count = len(maintanance)

	def buy_now_property(self):
		if self.invoice_ids:
			if any(inv.state =='paid' for inv in self.invoice_ids):
				raise UserError(_("This property (%s) already sold out..!")%self.name)
		if self.property_book_for != 'sale':
			raise UserError(_("This property only allow for Rent..!"))
		if self.property_price < 1:
			raise UserError(_("Please enter valid property price for (%s)..!") % self.name)

		view_id = self.env.ref('property_rental_mgt_app.property_buy_wizard')
		if self.reasonable_price:
			property_price = self.discounted_price
		else:
			property_price = self.property_price
		if view_id:
			buy_property_data = {
				'name' : _('Purchase Property & Partial Payment'),
				'type' : 'ir.actions.act_window',
				'view_type' : 'form',
				'view_mode' : 'form',
				'res_model' : 'property.buy',
				'view_id' : view_id.id,
				'target' : 'new',
				'context' : {
							'property_id' : self.id,
							'desc' : self.description,
							'property_price':property_price,
							'owner_id':self.owner_id.id,
							'purchaser_id':self.env.user.partner_id.id,
							 },
			}
		return buy_property_data

	def reserve_property(self):
		if self.renter_history_ids:
			if all(each.state =='reserve' for each in self.renter_history_ids):
				raise UserError(_("This property already reserved..!"))

		if self.property_book_for != 'rent':
			raise UserError(_("This property only allow for sale..!"))
		if self.rent_price <= 0 or self.deposite <= 0:
			raise UserError(_("Please enter valid property rent or deposite price for (%s)..!") % self.name)
		view_id = self.env.ref('property_rental_mgt_app.property_book_wizard')

		if view_id:
			book_property_data = {
				'name' : _('Reserve Property & Contract Configure'),
				'type' : 'ir.actions.act_window',
				'view_type' : 'form',
				'view_mode' : 'form',
				'res_model' : 'property.book',
				'view_id' : view_id.id,
				'target' : 'new',
				'context' : {
							'property_id' :self.id,
							'desc' : self.description,
							'rent_price':self.rent_price,
							'renter_id':self.user_id.id or self.env.user.id,
							'owner_id':self.owner_id.id,
							'deposite':self.deposite,
							 },
			}
		return book_property_data

	def action_view_invoice(self):
		for rec in self:
			invoices = self.env['account.move'].search([('property_id','=',rec.id)])
			action = self.env.ref('account.action_move_out_invoice_type').read()[0]
			if len(invoices) > 1:
				action['domain'] = [('id', 'in', invoices.ids)]
			elif len(invoices) == 1:
				action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
				action['res_id'] = invoices.ids[0]
			else:
				action = {'type': 'ir.actions.act_window_close'}
			return action


	def action_view_maintenance(self):
		for rec in self:
			invoices = self.env['property.maintanance'].search([('property_id','=',rec.id)])
			action = self.env.ref('property_rental_mgt_app.action_maintanance').read()[0]
			if len(invoices) > 1:
				action['domain'] = [('id', 'in', invoices.ids)]
			elif len(invoices) == 1:
				action['views'] = [(self.env.ref('property_rental_mgt_app.property_maintanance_form').id, 'form')]
				action['res_id'] = invoices.ids[0]
			else:
				action = {'type': 'ir.actions.act_window_close'}
			return action


	# automatically set property to rentable state
	def property_set_to_available(self):
		contracts = self.env['contract.details'].search([('property_id','=',self.id)])
		if all(c.state == "expire" for c in contracts):
			self.write({'state':"rent"})
