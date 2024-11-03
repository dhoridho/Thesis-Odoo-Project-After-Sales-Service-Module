# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PosZReport(models.TransientModel):
	_name = "z.report.wizard"
	_description = "POS Z Report Wizard"

	pos_session_ids = fields.Many2many('pos.session', 'pos_sessions_close',string="POS Session(s)",domain="[('state', 'in', ['closed'])]",required=True)
	report_type = fields.Char('Report Type', readonly = True, default='PDF')
	company_id = fields.Many2one('res.company',"Company", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
	branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
	
	def generate_z_report(self):
		data = {'session_ids':self.pos_session_ids.ids,
				'company':self.company_id.id}
		return self.env.ref('equip3_pos_report.action_z_report_print').report_action([], data=data)