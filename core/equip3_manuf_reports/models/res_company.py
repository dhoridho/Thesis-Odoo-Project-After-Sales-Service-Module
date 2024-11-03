from odoo import models, fields, _


class ResCompany(models.Model):
	_inherit = 'res.company'

	def write(self, vals):
		res = super(ResCompany, self).write(vals)
		for company in self:
			if company.id == self.env.company.id and not company.manufacturing:
				manufacturing_cost_analysis_menu = self.env.ref("equip3_manuf_reports.menu_mrp_cost_analysis")
				if manufacturing_cost_analysis_menu:
					manufacturing_cost_analysis_menu.active = False
			else:
				manufacturing_cost_analysis_menu = self.env.ref("equip3_manuf_reports.menu_mrp_cost_analysis")
				if manufacturing_cost_analysis_menu:
					manufacturing_cost_analysis_menu.active = True

			if company.id == self.env.company.id:
				subcon_report_menu = self.env.ref('equip3_manuf_reports.menu_action_view_subcon_report')
				subcon_report_menu.active = company.use_subcontracting

		return res
