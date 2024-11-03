from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        internal_users = self.env['res.users'].search([('active', '=', True)])
        for rec in internal_users:
            if self.is_warehouse_shipments:
                self.env.ref('equip3_inventory_operations_countd.batch_operation_parent').active = True
                self.env.ref('equip3_inventory_operations_countd.batch_operation_pick_child').active = True
                self.env.ref('equip3_inventory_operations_countd.batch_operation_pack_child').active = True
                self.env.ref('equip3_inventory_operations_countd.batch_operation_delivery_child').active = True

            else:
                self.env.ref('equip3_inventory_operations_countd.batch_operation_parent').active = False
                self.env.ref('equip3_inventory_operations_countd.batch_operation_pick_child').active = False
                self.env.ref('equip3_inventory_operations_countd.batch_operation_pack_child').active = False
                self.env.ref('equip3_inventory_operations_countd.batch_operation_delivery_child').active = False

        return res
