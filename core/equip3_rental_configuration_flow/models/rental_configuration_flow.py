from odoo import api, fields, models, _


class RentalConfigurationFlow(models.TransientModel):
    _name = 'rental.configuration.flow'

    name = fields.Char('Name', default='Rental Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result
