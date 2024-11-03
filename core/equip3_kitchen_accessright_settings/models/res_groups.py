from odoo import models


class GroupsView(models.Model):
    _inherit = 'res.groups'

    def get_application_groups(self, domain):
        kitchen_domain = [('category_id', '!=', self.env.ref('equip3_kitchen_accessright_settings.module_central_kitchen').id)]
        if not self.env.company.central_kitchen:
            domain += kitchen_domain
        return super(GroupsView, self).get_application_groups(domain)
