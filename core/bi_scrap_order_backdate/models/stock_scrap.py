# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime,date, timedelta




class InheritStockScrap(models.Model):
	_inherit = 'stock.scrap'

	move_remarks_scrap = fields.Char('Remarks', readonly=True)

	def action_validate(self):

		return {
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'wizard.scrap.order.backdate',
					'type': 'ir.actions.act_window',
					'target': 'new',
					'res_id': False,
					'context': self.env.context,
					}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
