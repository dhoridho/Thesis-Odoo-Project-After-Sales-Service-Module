from odoo import models, fields, api, tools


class IrUiMenuCategory(models.Model):
    _name = 'ir.ui.menu.category'
    _description = 'Menu Category'

    sequence = fields.Integer(required=True)
    name = fields.Char(required=True, copy=False)
    color = fields.Char(default='#FFFFFF')


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _default_menu_category(self):
        utilities_category = self.env.ref('equip3_hashmicro_ui.category_utilities', raise_if_not_found=False)
        return utilities_category and utilities_category.id or False

    equip_icon_class = fields.Char(string='Icon Class')
    equip_category_id = fields.Many2one('ir.ui.menu.category', string='Category', default=_default_menu_category)

    def read(self, fields=None, load='_classic_read'):
        if fields and isinstance(fields, list):
            fields += ['complete_name', 'equip_icon_class', 'equip_category_id']
        result = super(IrUiMenu, self).read(fields=fields, load=load)
        utilities_category = self.env.ref('equip3_hashmicro_ui.category_utilities', raise_if_not_found=False)
        if not utilities_category:
            return result
        for i, res in enumerate(result):
            if not res['equip_category_id']:
                result[i]['equip_category_id'] = (utilities_category.id, utilities_category.name)
        return result
