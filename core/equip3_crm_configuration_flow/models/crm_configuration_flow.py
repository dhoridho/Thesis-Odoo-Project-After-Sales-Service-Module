from odoo import api, fields, models, _


class CRMConfigurationFlow(models.TransientModel):
    _name = 'crm.configuration.flow'
    _description = 'CRM Configuration Flow'

    name = fields.Char('Name', default='CRM Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result