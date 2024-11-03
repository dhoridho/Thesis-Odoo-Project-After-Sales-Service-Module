from odoo import api, fields, models, _


class CateringConfigurationFlow(models.TransientModel):
    _name = 'catering.configuration.flow'

    name = fields.Char('Name', default='Catering Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result
