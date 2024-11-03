from odoo import api, fields, models, modules, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_cost_price_per_warehouse = fields.Boolean(string="Is Cost price per warehouse?",readonly=False)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        res['is_cost_price_per_warehouse'] = self.env['ir.config_parameter'].sudo().get_param('is_cost_price_per_warehouse')

        return res

    @api.model
    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param('is_cost_price_per_warehouse', self.is_cost_price_per_warehouse)
        super(ResConfigSettings, self).set_values()