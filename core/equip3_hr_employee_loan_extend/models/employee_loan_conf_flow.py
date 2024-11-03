from odoo import api, fields, models, _

class LoanConfigurationFlow(models.TransientModel):
    _name = 'loan.configuration.flow'

    name = fields.Char('Name', default='Loan Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result