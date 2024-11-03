from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PropertyProduct(models.Model):
	_inherit = 'product.product'

	agreement_id = fields.Many2one('agreement', string='Agreement', domain=[('is_template', '=', False)])	
	state = fields.Selection([('draft','Draft'),('rent','Rentable'),('sale','Saleable'),('reserve','Reserve'),('sold','Sold'),('cancel','Cancelled')], string="Property Status", track_visibility="onchange", help='State of the Propertsy', group_expand='_read_group_state')
	contract_count = fields.Integer(compute='_compute_contract_count', string='Contract Count')

	@api.model
	def _read_group_state(self, stages, domain, order):
		state = ['draft','rent','sale','reserve','sold','cancel']
		return state

	def _compute_contract_count(self):
		for rec in self:
			rec.contract_count = self.env['agreement'].search_count([('property_id', '=', rec.id)])

	def view_contract_action(self):
			return{
				'name': 'Contracts',
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'agreement',
				'domain': [('property_id', '=', self.id)],
				'type': 'ir.actions.act_window',
			}

	# move code from equip3_property_operation_contract
	def button_confirm(self):
		if self.state == 'draft' and self.property_book_for == 'sale':
			if self.property_price <= 0 or self.discounted_price <= 0:
				raise UserError(_("Please enter valid property price or reasonable amount...!"))
			self.state = 'sale'
		if self.state == 'draft' and self.property_book_for == 'rent':
			if self.rent_price <= 0 or self.deposite <= 0:
				raise UserError(_("Please enter valid property rent amount...!"))
			contracts = self.env['agreement'].search([("is_template", "=", True)])
			if not contracts:
				raise UserError(_("Please first create contract template for property rental...!(Contract Management -> Configuration -> Templates)"))
			self.state = 'rent'

		if self.user_commission_ids:
			for each in self.user_commission_ids:
				if each.percentage <= 0:
					raise UserError(_("Please enter valid commission percentage in commission lines...!"))


	def buy_now_property_(self):
		if self.agreement_id:
			raise UserError(_("This property (%s) already sold out..!")%self.name)
		if self.property_book_for != 'sale':
			raise UserError(_("This property only allow for Rent..!"))
		if self.property_price < 1:
			raise UserError(_("Please enter valid property price for (%s)..!") % self.name)

		view_id = self.env.ref('equip3_property_operation.property_buy_contract_wizard')
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
				'res_model' : 'property.buy.contract',
				'view_id' : view_id.id,
				'target' : 'new',
				'context' : {
							'property_id' : self.id,
							'property_price':property_price,
							'purchaser_id':self.env.user.partner_id.id,
							},
			}
		return buy_property_data

	def reserve_property(self):
		res = super(PropertyProduct, self).reserve_property()
		res['context']['owner_id'] = self.property_owner_id.id
		return res

	def reserve_property_contract(self):

		if self.property_book_for != 'rent':
			raise UserError(_("This property only allow for sale..!"))
		if self.rent_price <= 0 or self.deposite <= 0:
			raise UserError(_("Please enter valid property rent or deposite price for (%s)..!") % self.name)
		view_id = self.env.ref('equip3_property_operation.property_rent_contract_wizard')

		if view_id:
			book_property_data = {
				'name' : _('Reserve Property & Contract Configure'),
				'type' : 'ir.actions.act_window',
				'view_type' : 'form',
				'view_mode' : 'form',
				'res_model' : 'property.rent.contract',
				'view_id' : view_id.id,
				'target' : 'new',
				'context' : {
							'property_id' :self.id,
							'renter_id':self.user_id.id or self.env.user.id,
							'deposite':self.deposite,
							'deposite_daily':self.daily_rent,
							'deposite_yearly':self.rent_price,
								},
			}
		return book_property_data