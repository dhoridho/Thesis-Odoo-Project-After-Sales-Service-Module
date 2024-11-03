# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class all_loyalty_setting(models.Model):
	_inherit = 'all.loyalty.setting'

	company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)

	@api.constrains('issue_date', 'expiry_date', 'active', 'company_id')
	def check_date(self):
		if self.expiry_date < self.issue_date :
			msg = _("Expiry Date should not be smaller than Issue Date. please change dates.")
			raise ValidationError(msg)
		flag = False
		loyalty_rec = self.env['all.loyalty.setting'].search([('id', '!=', self.id), ('active', '=', True),
															  ('company_id', '=', self.company_id.id)])
		for record in loyalty_rec:
			if (record.issue_date <= self.issue_date <= record.expiry_date) or \
					(record.issue_date <= self.expiry_date <= record.expiry_date):
				flag = True
			if record.issue_date >= self.issue_date <= record.expiry_date:
				flag = True
		if flag:
			msg = _("You can not apply two Loyalty Configuration within same date range please change dates.")
			raise ValidationError(msg)
