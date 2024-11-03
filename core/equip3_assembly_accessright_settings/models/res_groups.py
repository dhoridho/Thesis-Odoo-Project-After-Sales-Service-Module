from odoo import models


class GroupsView(models.Model):
    _inherit = 'res.groups'

    def get_application_groups(self, domain):
        assembly_domain = [('category_id', '!=', self.env.ref('equip3_assembly_accessright_settings.module_assembly').id)]
        if not self.env.company.assembly:
            domain += assembly_domain
        return super(GroupsView, self).get_application_groups(domain)
