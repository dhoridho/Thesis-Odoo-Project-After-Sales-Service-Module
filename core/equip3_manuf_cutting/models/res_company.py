from odoo import models, fields, api
import random


class ResCompany(models.Model):
	_inherit = 'res.company'

	is_cutting_plan = fields.Boolean('Cutting Plan')
	is_cutting_order = fields.Boolean('Cutting Order')

	def write(self, vals):
		res = super(ResCompany, self).write(vals)
		menu_cutting_root = self.env.ref('equip3_manuf_cutting.menu_cutting_root')
		menu_approval_matrix = self.env.ref('equip3_manuf_cutting.menu_cutting_approval_matrix')
		menu_cutting_plan = self.env.ref("equip3_manuf_cutting.menu_cutting_cutting_plan")
		menu_cutting_order = self.env.ref("equip3_manuf_cutting.menu_cutting_cutting_order")
		for company in self:
			if not company == self.env.company:
				continue
			menu_cutting_root.active = company.cutting
			menu_approval_matrix.active = company.is_cutting_plan or company.is_cutting_order or False
			menu_cutting_plan.active = company.is_cutting_plan
			menu_cutting_order.active = company.is_cutting_order
		return res
