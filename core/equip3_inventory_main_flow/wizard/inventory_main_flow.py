from odoo import api, models, fields

class InventoryMainFlow(models.TransientModel):
    _name = 'inventory.main.flow'
    _description = 'Inventory Main Flow'
    name = fields.Char(string='Name', default='Inventory Main Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result