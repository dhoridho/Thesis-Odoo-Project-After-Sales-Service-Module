from odoo import api, fields, models, _

class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    prefix_limit = fields.Integer(string="Prefix Limit", default=5)
    

    @api.model
    def get_values(self):
        res = super(ResConfigSettingsInherit, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update(
            prefix_limit=ICP.get_param('prefix_limit', 5),
        )
        return res

    def set_values(self):
        res = super(ResConfigSettingsInherit, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('prefix_limit', self.prefix_limit)
        return res
