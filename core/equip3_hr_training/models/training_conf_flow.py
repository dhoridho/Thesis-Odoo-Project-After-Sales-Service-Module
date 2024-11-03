from odoo import api, fields, models, _

class TrainingConfigurationFlow(models.TransientModel):
    _name = 'training.configuration.flow'

    name = fields.Char('Name', default='Training Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result