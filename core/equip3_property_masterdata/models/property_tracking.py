from odoo import api, fields, models
import requests
import urllib.parse
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta



class PropertyTracking(models.Model):
    _name = 'property.tracking'
    _description = 'Property Tracking'

    name = fields.Char(string='Name', default='Property Tracking')

class PropertyProduct(models.Model):
    _inherit = 'product.product'

    # property_lat = fields.Char(string="latitute", store=True)
    # property_lng = fields.Char(string="logtitude", store=True)

    @api.model
    def convert_address_into_geocodes(self):
        location = []
        product_id = self.env['product.product'].search([('is_property','=',True),('type','=','property')])
        for rec in product_id:

            address = ""
            if rec.street:
                address += rec.street + ","
            if rec.location:
                address += rec.location + ","
            if rec.city:
                address += rec.city + ","
            if rec.zipcode != 0:
                address += str(rec.zipcode)+ ","
            if rec.state_id:
                address += str(rec.state_id.name) + ","
            if rec.country_id:
                address += str(rec.country_id.name)

            url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(address) + '?format=json'
            response = requests.get(url).json()

            if response:
                location.append({'lat': response[0]['lat'],
                                 'lng': response[0]['lon']
                                 })
        return location

