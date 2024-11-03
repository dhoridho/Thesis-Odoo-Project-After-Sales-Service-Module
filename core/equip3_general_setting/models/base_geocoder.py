import requests
import logging

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

class GeoCoder(models.AbstractModel):
    """
    Abstract class used to call Geolocalization API and convert addresses
    into GPS coordinates.
    """
    _inherit = "base.geocoder"

    @api.model
    def _call_googlemap(self, addr, **kw):
        """ Use google maps API. It won't work without a valid API key.
        :return: (latitude, longitude) or None if not found
        """
        apikey = self.env['ir.config_parameter'].sudo().get_param('base_geolocalize.google_map_api_key')
        if not apikey:
            raise UserError(_(
                "API key for GeoCoding (Places) required.\n"
                "Visit https://developers.google.com/maps/documentation/geocoding/get-api-key for more information."
            ))
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {'sensor': 'false', 'address': addr, 'key': apikey}
        if kw.get('force_country'):
            params['components'] = 'country:%s' % kw['force_country']
        try:
            result = requests.get(url, params).json()
        except Exception as e:
            self._raise_query_error(e)

        try:
            if result['status'] == 'ZERO_RESULTS':
                return None
            # if result['status'] != 'OK':
                # _logger.debug('Invalid Gmaps call: %s - %s',
                #               result['status'], result.get('error_message', ''))
                # error_msg = _('Unable to geolocate, received the error:\n%s'
                #               '\n\nGoogle made this a paid feature.\n'
                #               'You should first enable billing on your Google account.\n'
                #               'Then, go to Developer Console, and enable the APIs:\n'
                #               'Geocoding, Maps Static, Maps Javascript.\n') % result.get('error_message')
                # raise UserError(error_msg)
            geo = result['results'][0]['geometry']['location']
            return float(geo['lat']), float(geo['lng'])
        except (KeyError, ValueError):
            _logger.debug('Unexpected Gmaps API answer %s', result.get('error_message', ''))
            return None

    def _raise_query_error(self, error):
        return False