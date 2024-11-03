# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api, _
from datetime import datetime, timedelta


class PurchaseAgreement(models.Model):
	_inherit = "purchase.agreement"
	
	partner_id = fields.Many2one('res.partner', 'Partner', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('state', '=', 'approved')]")
	partner_ids = fields.Many2many(
		'res.partner', string='Vendors', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True)