from odoo import models


class GroupsView(models.Model):
	_inherit = 'res.groups'

	def get_application_groups(self, domain):
		extra_domain = [('category_id', '!=', self.env.ref('equip3_mining_accessright_settings.module_category_equip3_mining_accessright_settings').id)]
		if not self.env.company.mining:
			domain += extra_domain
		return super(GroupsView, self).get_application_groups(domain)
