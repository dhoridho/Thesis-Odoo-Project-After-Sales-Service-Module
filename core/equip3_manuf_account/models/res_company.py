from odoo import models, fields


class ResCompany(models.Model):
	_inherit = 'res.company'

	def write(self, vals):
		res = super(ResCompany, self).write(vals)
		menu_mrp_cost_act = self.env.ref("equip3_manuf_account.menu_finance_entries_manufacturing")
		for company in self:
			if not company == self.env.company:
				continue
			menu_mrp_cost_act.active = company.manufacturing
		return res
