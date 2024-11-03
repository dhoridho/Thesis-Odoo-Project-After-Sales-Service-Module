# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime,date, timedelta
from odoo.tools import float_compare
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class WizardScrapOrder(models.TransientModel):
	_name = 'wizard.scrap.order.backdate'

	scrap_backdate = fields.Datetime('Backdate',required=True)
	scrap_remarks = fields.Char('Remarks', required=True)

	def scrap_order_confirm(self):

		today = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
		back_date = self.scrap_backdate.strftime(DEFAULT_SERVER_DATE_FORMAT)
		
		if back_date == today or back_date > today:
			raise ValidationError(_('You Can Select Back Date Only.'))

		stock_scrap_id = self.env['stock.scrap'].browse(self._context.get('active_id'))

		stock_scrap_id.do_scrap()

		jornal_id = self.env['account.journal'].search([('code', '=', 'MISC')])

		stock_scrap_id.write({'date_done':self.scrap_backdate,'move_remarks_scrap':self.scrap_remarks})

		for stock_scrap_move in stock_scrap_id.move_id:
			stock_scrap_move.write({'date':self.scrap_backdate,'move_remarks':self.scrap_remarks})

			custom_accountmove = self.env['account.move'].create({'date':self.scrap_backdate,
				'journal_id':jornal_id.id,'stock_move_id':stock_scrap_move.id})

			self.env['account.move.line'].create({'partner_id':3,'account_id':1,
				'name':'MO Transfer','move_id':custom_accountmove.id})

			custom_accountmove.post()

			for stock_scrap_move_line in stock_scrap_move.move_line_ids:
				stock_scrap_move_line.write({'date':stock_scrap_move.date,
					'move_remarks_line':self.scrap_remarks})



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: