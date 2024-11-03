from odoo import api, fields, models, _

class RecruitmentConfigurationFlow(models.TransientModel):
    _name = 'recruitment.configuration.flow'

    name = fields.Char('Name', default='Recruitment Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result