from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _default_open_weather_theme(self):
        return self.env.ref('equip3_open_weather.open_weather_theme_data_2', raise_if_not_found=False)

    @api.model
    def _default_open_weather_widget(self):
        return self.env.ref('equip3_open_weather.open_weather_widget_data_11', raise_if_not_found=False)

    oweather_apikey = fields.Char(string='Open Weather API Key', config_parameter='equip3_open_weather.oweather_apikey')
    oweather_units = fields.Selection(selection=[
        ('metric', 'Celcius'),
        ('imperial', 'Fahrenheit')
    ], default='metric', string='Open Weather Units', config_parameter='equip3_open_weather.oweather_units')
    oweather_theme_id = fields.Many2one('open.weather.theme', string='Open Weather Theme', config_parameter='equip3_open_weather.oweather_theme', default=_default_open_weather_theme)
    oweather_widget_id = fields.Many2one('open.weather.widget', string='Open Weather Widget', config_parameter='equip3_open_weather.oweather_widget', default=_default_open_weather_widget, domain="[('theme_id', '=', oweather_theme_id)]")

    @api.model
    def get_open_weather_data(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        return {
            'apikey': ir_config.get_param('equip3_open_weather.oweather_apikey'),
            'units': ir_config.get_param('equip3_open_weather.oweather_units'),
            'widget': self.env['open.weather.widget'].browse(int(ir_config.get_param('equip3_open_weather.oweather_widget'))).oid,
            'city': self.env.user.partner_id.oweather_city_id
        }

    @api.onchange('oweather_theme_id')
    def _onchange_oweather_theme_id(self):
        if not self.oweather_theme_id:
            self.oweather_widget_id = False
        else:
            if self.oweather_widget_id:
                theme_widget = self.env['open.weather.widget'].search([
                    ('theme_id', '=', self.oweather_theme_id.id),
                    ('name', '=', self.oweather_widget_id.name)
                ], limit=1)
                self.oweather_widget_id = theme_widget.id
