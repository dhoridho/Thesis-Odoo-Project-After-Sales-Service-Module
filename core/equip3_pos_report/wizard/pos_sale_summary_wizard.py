# -*- coding: utf-8 -*-

from odoo import fields, models

class PosSalesSummaryWizard(models.TransientModel):
	_name = "pos.sale.summary.wizard"
	_description = "POS Sale Summary Wizard"

	start_dt = fields.Date('Start Date', required = True)
	end_dt = fields.Date('End Date', required = True)
	report_type = fields.Char('Report Type', readonly = True, default='PDF')
	only_summary = fields.Boolean('Only Summary')
	res_user_ids = fields.Many2many('res.users', default=lambda s: s.env['res.users'].search([]))
	company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)
	pos_branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])

	def sale_summary_generate_report(self):
		return self.env.ref('equip3_pos_report.action_sales_summary_report').report_action(self)
