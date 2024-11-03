from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests, json, googlemaps


class ProviderGrid(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('delivery_boy', 'Delivery Boy')], ondelete={'delivery_boy': 'cascade'})

    def delivery_boy_rate_shipment(self, order):
        carrier = self._match_address(order.partner_shipping_id)
        if not carrier:
            return {
                        'success': False,
                        'price': 0.0,
                        'error_message': _('Error: this delivery method is not available for this address.'),
                        'warning_message': False
                   }

        else:
            order.partner_shipping_id.geo_localize()
            order.warehouse_id.partner_id.geo_localize()

            google_api_key = self.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
            gmaps = googlemaps.Client(key=google_api_key)

            source = (order.warehouse_id.partner_id.partner_latitude, order.warehouse_id.partner_id.partner_longitude)
            destination = (order.partner_shipping_id.partner_latitude, order.partner_shipping_id.partner_longitude)

            distance = gmaps.distance_matrix(source, destination)["rows"][0]["elements"][0]["distance"]

            if distance:
                order.distance_btn_2_loc = distance['value'] * 0.002
                return {
                    'success': True,
                    'price': order.distance_btn_2_loc*self.env.user.company_id.company_delivery_rate,
                    'error_message': False,
                    'warning_message': False
                }

            else:
                return {
                    'success': False,
                    'price': 0.0,
                    'error_message': _('Error: this delivery method is not available for this address.'),
                    'warning_message': False
                }

