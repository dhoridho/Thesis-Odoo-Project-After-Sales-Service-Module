# -*- coding: utf-8 -*-

from odoo import fields, models

class PosSession(models.Model):
	_inherit = 'pos.session'

	is_pos_config_save_order_history_local = fields.Boolean('POS Config: Is Save Order History Local', compute='_compute_is_pos_config_save_order_history_local')

	def _compute_is_pos_config_save_order_history_local(self):
		for rec in self:
			is_true = False
			if rec.config_id.is_save_order_history_local:
				is_true = rec.config_id.is_save_order_history_local
			rec.is_pos_config_save_order_history_local = is_true