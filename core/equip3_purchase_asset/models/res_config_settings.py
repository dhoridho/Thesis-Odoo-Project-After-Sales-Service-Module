
from odoo import models, fields, _


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'
    
    def set_values(self):
        super(ResConfigSetting, self).set_values()
        if self.is_good_services_order:
            self.env.ref("equip3_purchase_asset.menu_purchase_assets_order").active = True
        else:
            self.env.ref("equip3_purchase_asset.menu_purchase_assets_order").active = False

        if self.is_purchase_request_assign_user:
            # self.env.ref("equip3_purchase_asset.menu_purchase_request_lines_categ").active = True
            self.env.ref("equip3_purchase_asset.menu_purchase_request_lines").active = False
            self.env.ref("equip3_purchase_asset.menu_purchase_request_lines_not_assigned").active = True
            self.env.ref("equip3_purchase_asset.menu_purchase_request_lines_assigned").active = True
        else:
            # self.env.ref("equip3_purchase_asset.menu_purchase_request_lines_categ").active = False
            self.env.ref("equip3_purchase_asset.menu_purchase_request_lines").active = True
            self.env.ref("equip3_purchase_asset.menu_purchase_request_lines_not_assigned").active = False
            self.env.ref("equip3_purchase_asset.menu_purchase_request_lines_assigned").active = False