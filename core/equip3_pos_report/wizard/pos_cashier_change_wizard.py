# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
 

class POSCashierChangeWizard(models.TransientModel):
	_name = "pos.cashier.change.wizard"
	_description ="POS Cashier Change Wizard"


	start_datetime = fields.Datetime('Start Date')
	end_datetime = fields.Datetime('End Date')
	pos_branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])


	def generate_report(self):
		data = self.env['pos.login.history'].search([('checkin_datetime','>=',self.start_datetime),('checkout_datetime','<=',self.end_datetime)])
		if not data:
			raise UserError(_('No have data to print.'))
		return self.env.ref('equip3_pos_report.act_report_pos_login_history_report').report_action(data)