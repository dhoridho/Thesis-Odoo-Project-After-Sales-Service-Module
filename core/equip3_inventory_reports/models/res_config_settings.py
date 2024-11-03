
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()

        if self.internal_type == 'with_transit':
            self.env.ref('equip3_inventory_reports.menu_inventory_in_transit').active = True
        else:
            self.env.ref('equip3_inventory_reports.menu_inventory_in_transit').active = False
