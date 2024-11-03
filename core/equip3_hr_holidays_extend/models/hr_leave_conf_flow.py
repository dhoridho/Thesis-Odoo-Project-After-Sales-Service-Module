from odoo import api, fields, models, _

class HrLeaveConfigurationFlow(models.TransientModel):
    _name = 'hr.leave.configuration.flow'

    name = fields.Char('Name', default='HR Leave Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result
