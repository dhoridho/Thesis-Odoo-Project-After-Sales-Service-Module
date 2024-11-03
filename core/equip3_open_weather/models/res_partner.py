import requests
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    oweather_city_id = fields.Char(string='Open Weather City ID')

    @api.model
    def create(self, vals):
        partners = super(ResPartner, self).create(vals)
        if not vals.get('partner_latitude') and not vals.get('partner_longitude'):
            return partners
        partners._assign_open_weather_city_id()
        return partners

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        if not vals.get('partner_latitude') and not vals.get('partner_longitude'):
            return res
        self._assign_open_weather_city_id()
        return res

    def _assign_open_weather_city_id(self):
        apikey = self.env['ir.config_parameter'].sudo().get_param('equip3_open_weather.oweather_apikey', False)
        if not apikey:
            _logger.error(_("There was a problem when fetching Open Weather city data: Please set Open Weather API Key"))
            return
        
        for partner in self:
            latitude = partner.partner_latitude
            longitude = partner.partner_longitude
            if not latitude or not longitude:
                continue

            try:
                url = f'https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={apikey}'
                data = requests.get(url).json()
                partner.oweather_city_id = str(data['id'])
            except Exception as err:
                _logger.error(_("There was a problem when fetching Open Weather city data: %s" % err))
