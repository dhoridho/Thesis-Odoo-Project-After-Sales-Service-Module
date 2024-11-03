# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from ast import literal_eval

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	remainder_mail = fields.Integer('Reminder Days For Rental Expiration Mail', default="15")
	saleable_rental_details = fields.Boolean("Add saleable product in rental order", default = False)

	@api.model
	def get_values(self):
		res = super(ResConfigSettings, self).get_values()
		get_param = self.env['ir.config_parameter'].sudo().get_param
		res.update(
			remainder_mail=int(get_param('browseinfo_rental_management.remainder_mail')),
			saleable_rental_details = get_param('browseinfo_rental_management.remainder_mail')

		)
		return res

	def set_values(self):
		super(ResConfigSettings, self).set_values()
		set_param = self.env['ir.config_parameter'].sudo().set_param
		# we store the repr of the values, since the value of the parameter is a required string
		set_param('browseinfo_rental_management.remainder_mail', self.remainder_mail)
		set_param('browseinfo_rental_management.saleable_rental_details', self.saleable_rental_details)
