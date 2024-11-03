# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError


class CRMTeam(models.Model):
	_inherit = 'crm.team'

	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True, readonly=True)
	member_ids = fields.One2many(
        'res.users', 'sale_team_id', string='Channel Members',
        check_company=True,
        help="Add members to automatically assign their documents to this sales team. You can only be member of one team.")
	
	@api.onchange('user_id')
	def member_ids_onchange(self):
		for rec in self:
			company_id = self.env.company.id
			members=self.env['res.users'].search([('share', '=', False)]).filtered(lambda u,company_id=company_id:company_id in u.company_ids.ids).filtered(lambda u: rec.user_id.id != u.id).mapped('name')
			return {'domain': {'member_ids': ['&', ('share', '=', False), ('name', 'in', members)]}}

	@api.constrains('user_id', 'member_ids')
	def member_ids_constrains(self):
		for rec in self:
			for member in rec.member_ids:
				print(f'\n\nuser_id: {rec.user_id.id}')
				print(f'member : {member.id}\n\n')
				if member.id == rec.user_id.id:
					raise ValidationError('Team leader cannot be a team member')