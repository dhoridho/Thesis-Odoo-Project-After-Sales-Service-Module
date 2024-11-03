# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MaintenanceStage(models.Model):
	_inherit = 'maintenance.stage'

	custom_user_ids = fields.Many2many('res.users', string='Allow Users', help="Selected users can move maintenance request into this stage.")