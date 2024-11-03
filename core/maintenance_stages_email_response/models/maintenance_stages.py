# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MaintenanceStage(models.Model):
	_inherit = "maintenance.stage"

	custom_mail_template_id = fields.Many2one(
		'mail.template',
		string='Email Template',
		domain=[('model', '=', 'maintenance.request')]
	)
	