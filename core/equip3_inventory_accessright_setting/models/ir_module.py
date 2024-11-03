from odoo import models


class Module(models.Model):
    _inherit = "ir.module.module"

    def button_immediate_upgrade(self):
        res = super(Module, self).button_immediate_upgrade()

        if self.name in ["equip3_inventory_accessright_setting"]:
            set_warehouse_sublevel = self.env['ir.config_parameter'].get_param('set_warehouse_sublevel', False)
            warehouse_sublevel_zone = self.env['ir.config_parameter'].get_param('warehouse_sublevel_zone', False)
            warehouse_sublevel_shelf = self.env['ir.config_parameter'].get_param('warehouse_sublevel_shelf', False)
            warehouse_sublevel_rack = self.env['ir.config_parameter'].get_param('warehouse_sublevel_rack', False)
            warehouse_sublevel_bin = self.env['ir.config_parameter'].get_param('warehouse_sublevel_bin', False)

            if set_warehouse_sublevel:
                self.env.ref('equip3_inventory_accessright_setting.menu_manage_wh_sublevel').active = True
            else:
                self.env.ref('equip3_inventory_accessright_setting.menu_manage_wh_sublevel').active = False

            if warehouse_sublevel_zone:
                self.env.ref('equip3_inventory_accessright_setting.menu_wh_sublevel_zone').active = True
            else:
                self.env.ref('equip3_inventory_accessright_setting.menu_wh_sublevel_zone').active = False

            if warehouse_sublevel_shelf:
                self.env.ref('equip3_inventory_accessright_setting.menu_wh_sublevel_shelf').active = True
            else:
                self.env.ref('equip3_inventory_accessright_setting.menu_wh_sublevel_shelf').active = False

            if warehouse_sublevel_rack:
                self.env.ref('equip3_inventory_accessright_setting.menu_wh_sublevel_rack').active = True
            else:
                self.env.ref('equip3_inventory_accessright_setting.menu_wh_sublevel_rack').active = False

            if warehouse_sublevel_bin:
                self.env.ref('equip3_inventory_accessright_setting.menu_wh_sublevel_bin').active = True
            else:
                self.env.ref('equip3_inventory_accessright_setting.menu_wh_sublevel_bin').active = False

        return res
