# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MaintenanceRequest(models.Model):
	_inherit = "maintenance.request"


	def _track_template(self, changes):
		res = super(MaintenanceRequest, self)._track_template(changes)
		custom_maintenance = self[0]
		if 'stage_id' in changes and custom_maintenance.stage_id.custom_mail_template_id:
			res['stage_id'] = (custom_maintenance.stage_id.custom_mail_template_id, {
				'auto_delete_message': True,
				'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
				'email_layout_xmlid': 'mail.mail_notification_light'
			})
		return res