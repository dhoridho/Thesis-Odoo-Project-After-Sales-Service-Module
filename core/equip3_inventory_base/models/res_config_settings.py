from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_cost_per_warehouse = fields.Boolean(config_parameter='equip3_inventory_base.is_cost_per_warehouse')

    stock_inventory_validation_scheduler = fields.Boolean(string='Inventory Adjustment Scheduler', config_parameter='equip3_inventory_base.stock_inventory_validation_scheduler', default=False)
    stock_inventory_validation_per_batch = fields.Integer(string='Inventory Adjustment Lines per Batch', config_parameter='equip3_inventory_base.stock_inventory_validation_per_batch', default=500)

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        menu = self.env.ref('equip3_inventory_base.menu_action_view_stock_inventory_log', raise_if_not_found=False)
        res['stock_inventory_validation_scheduler'] = menu.active if menu else False
        return super(ResConfigSettings, self).get_values()

    def set_values(self):
        menu = self.env.ref('equip3_inventory_base.menu_action_view_stock_inventory_log', raise_if_not_found=False)
        if menu:
            menu.active = self.stock_inventory_validation_scheduler
        return super(ResConfigSettings, self).set_values()
