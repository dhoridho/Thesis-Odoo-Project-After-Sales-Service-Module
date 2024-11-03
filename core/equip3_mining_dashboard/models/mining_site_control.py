import logging, requests
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)


class MiningSiteControl(models.Model):
    _inherit = 'mining.site.control'
    
    longitude = fields.Float(string="Longitude")
    latitude = fields.Float(string="Latitude")
    pit_ids = fields.One2many(comodel_name='mining.project.control', inverse_name='mining_site_id', string='Pits')

    def get_open_weather_data(self):
        self.ensure_one()
        ir_config = self.env['ir.config_parameter'].sudo()
        apikey = ir_config.get_param('equip3_open_weather.oweather_apikey')
        if not apikey:
            _logger.error(_("There was a problem when fetching Open Weather city data: Please set Open Weather API Key"))
            return {}

        try:
            url = f'https://api.openweathermap.org/data/2.5/weather?lat={self.latitude}&lon={self.longitude}&appid={apikey}'
            data = requests.get(url).json()
            city_id = str(data['id'])
        except Exception as err:
            city_id = '2643743' # default to London
            _logger.error(_("There was a problem when fetching Open Weather city data: %s" % err))

        return {
            'apikey': apikey,
            'units': ir_config.get_param('equip3_open_weather.oweather_units'),
            'widget': self.env['open.weather.widget'].browse(int(ir_config.get_param('equip3_mining_dashboard.oweather_site_widget'))).oid,
            'city': city_id
        }
