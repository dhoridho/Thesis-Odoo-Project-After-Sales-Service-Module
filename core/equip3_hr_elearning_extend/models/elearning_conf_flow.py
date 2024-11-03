from odoo import api, fields, models, _

class ElearningConfigurationFlow(models.TransientModel):
    _name = 'elearning.configuration.flow'

    name = fields.Char('Name', default='E-learning Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result