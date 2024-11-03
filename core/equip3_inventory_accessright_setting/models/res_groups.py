from odoo import _, api, fields, models


class GroupsView(models.Model):
    _inherit = 'res.groups'

    def _get_hidden_extra_categories(self):
        return [
            'base.module_category_hidden',
            'base.module_category_extra',
            'base.module_category_usability',
            'equip3_inventory_accessright_setting.module_category_equip3_inventory_accessright_setting'
        ]
