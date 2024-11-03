from odoo import api, fields, models, _


class SaleConfigurationFlow(models.TransientModel):
    _name = 'sale.configuration.flow'
    _description = "Sale Configuration Flow"

    name = fields.Char('Name', default='Sales Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result
