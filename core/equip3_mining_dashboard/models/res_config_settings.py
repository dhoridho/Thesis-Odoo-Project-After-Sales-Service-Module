from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _default_open_weather_site_theme(self):
        return self.env.ref('equip3_open_weather.open_weather_theme_data_2', raise_if_not_found=False)

    @api.model
    def _default_open_weather_site_widget(self):
        return self.env.ref('equip3_open_weather.open_weather_widget_data_11', raise_if_not_found=False)

    oweather_site_theme_id = fields.Many2one('open.weather.theme', string='Open Weather Site Theme', config_parameter='equip3_mining_dashboard.oweather_site_theme', default=_default_open_weather_site_theme)
    oweather_site_widget_id = fields.Many2one('open.weather.widget', string='Open Weather Site Widget', config_parameter='equip3_mining_dashboard.oweather_site_widget', default=_default_open_weather_site_widget, domain="[('theme_id', '=', oweather_site_theme_id)]")
