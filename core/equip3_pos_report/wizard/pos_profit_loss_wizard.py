# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import datetime
from dateutil import relativedelta

class PosProfitLossWizard(models.TransientModel):
	_name = "pos.profit.loss.wizard"
	_description = "POS Profit Loss Wizard"

	start_dt = fields.Date('Start Date', required = True, default=datetime.now().strftime('%Y-%m-01'))
	end_dt = fields.Date('End Date', required = True, 
		default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
	pos_branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
	
	
	def pos_profit_loss_report(self):
		return self.env.ref('equip3_pos_report.action_profit_loss_report').report_action(self)
