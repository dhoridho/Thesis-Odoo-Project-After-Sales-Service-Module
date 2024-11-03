from odoo import api, fields, models, _

class PayrollConfigurationFlow(models.TransientModel):
    _name = 'payroll.configuration.flow'

    name = fields.Char('Name', default='Payroll Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result