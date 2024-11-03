from odoo import _, api, fields, models

class ResGroups(models.Model):
    _inherit = 'res.groups'

    def _get_hidden_extra_categories(self):
        result = super(ResGroups, self)._get_hidden_extra_categories()
        result.append('equip3_pos_masterdata.module_equip3_pos_masterdata')
        result.append('base.module_category_point_of_sale')
        result.append('base.module_category_sales_point_of_sale')
        result.append('equip3_pos_masterdata.group_pos_user')
        result.append('equip3_pos_masterdata.group_pos_user')
        return result