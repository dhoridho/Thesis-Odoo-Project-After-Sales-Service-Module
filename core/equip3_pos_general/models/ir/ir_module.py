from odoo import models


class IRModule(models.Model):
    _inherit = "ir.module.module"

    def button_immediate_upgrade(self):
        apps_obj = self.env['ir.module.module'].sudo()
        res = super(IRModule, self).button_immediate_upgrade()
        if self.name in ["equip3_pos_general"]:
            module_pos_orders = apps_obj.search([('name','=','pos_orders'),('state','=','installed')],limit=1).sudo()
            if module_pos_orders:
                if len(module_pos_orders.downstream_dependencies(module_pos_orders))==1:
                    module_pos_orders.button_immediate_uninstall()
        return res