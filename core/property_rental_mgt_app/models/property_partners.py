# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
	_inherit = 'res.partner'

	partner_type = fields.Selection([('renter','Renter'),('purchaser','Purchaser'),('other','Other')])

class ResUser(models.Model):
	_inherit = 'res.users'

	@api.model
	def create(self, vals):
		res = super(ResUser, self).create(vals)
		renter = res.has_group('property_rental_mgt_app.group_rent_payer')
		purchaser = res.has_group('property_rental_mgt_app.group_purchaser')

		if renter:
			res.partner_id.write({'user_id':res.id, 'partner_type':'renter'})
		if purchaser:
			res.partner_id.write({'user_id':res.id, 'partner_type':'purchaser'})
		return res

	def write(self, vals):
		res = super(ResUser, self).write(vals)
		renter = self.env.ref('property_rental_mgt_app.group_rent_payer')
		purchaser = self.env.ref('property_rental_mgt_app.group_purchaser')

		if renter:
			if self.has_group('property_rental_mgt_app.group_rent_payer'):
				self.partner_id.write({'user_id':self.id, 'partner_type':'renter'})
		if purchaser:
			if self.has_group('property_rental_mgt_app.group_purchaser'):
				self.partner_id.write({'user_id':self.id, 'partner_type':'purchaser'})
		return res
