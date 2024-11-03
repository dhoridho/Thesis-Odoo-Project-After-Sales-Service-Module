from odoo import api, fields, models, _

class OvertimeConfigurationFlow(models.TransientModel):
    _name = 'overtime.configuration.flow'

    name = fields.Char('Name', default='Overtime Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result