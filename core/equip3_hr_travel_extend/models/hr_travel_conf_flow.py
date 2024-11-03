from odoo import api, fields, models, _

class TravelConfigurationFlow(models.TransientModel):
    _name = 'hr.travel.configuration.flow'

    name = fields.Char('Name', default='Talent Management Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result
