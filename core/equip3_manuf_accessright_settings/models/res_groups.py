from odoo import models


class GroupsView(models.Model):
    _inherit = 'res.groups'

    def get_application_groups(self, domain):
        category_ids = []
        for xml_id in ['base.module_category_manufacturing_manufacturing', 'equip3_manuf_accessright_settings.module_category_manufacturing_equip3']:
            try:
                category_id = self.env.ref(xml_id)
            except ValueError:
                continue
            category_ids += [category_id.id]
        manuf_domain = [('category_id', 'not in', category_ids)]
        if not self.env.company.manufacturing:
            domain += manuf_domain
        return super(GroupsView, self).get_application_groups(domain)
