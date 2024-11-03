from odoo import api, models, fields

class AssetFlow(models.TransientModel):
    _name = 'asset.flow'

    name = fields.Char(string='Name', default='Asset Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result