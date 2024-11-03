# # -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import requests
import urllib.parse



#
# # class PropertyRentalMgtAppModifier(http.Controller):
# #     @http.route('/property_rental_mgt_app_modifier/property_rental_mgt_app_modifier/', auth='public')
# #     def index(self, **kw):
# #         return "Hello, world"
#
# #     @http.route('/property_rental_mgt_app_modifier/property_rental_mgt_app_modifier/objects/', auth='public')
# #     def list(self, **kw):
# #         return http.request.render('property_rental_mgt_app_modifier.listing', {
# #             'root': '/property_rental_mgt_app_modifier/property_rental_mgt_app_modifier',
# #             'objects': http.request.env['property_rental_mgt_app_modifier.property_rental_mgt_app_modifier'].search([]),
# #         })
#
# #     @http.route('/property_rental_mgt_app_modifier/property_rental_mgt_app_modifier/objects/<model("property_rental_mgt_app_modifier.property_rental_mgt_app_modifier"):obj>/', auth='public')
# #     def object(self, obj, **kw):
# #         return http.request.render('property_rental_mgt_app_modifier.object', {
# #             'object': obj
# #         })
#
# # -*- coding: utf-8 -*-
# from odoo import http, _
# from odoo.http import request
#
class Equip3AssetPropertyTracking(http.Controller):

    @http.route('/property-detail/<int:property_id>', type='http', method=['GET'], website=True)
    def redirect_property_content(self,property_id, **kw):
        act_window_dict = request.env['ir.actions.act_window'].sudo()._for_xml_id('equip3_property_masterdata.product_property_action')
        redirect_url = request.httprequest.host_url+'web#id=%s&action=%s&model=product.product&view_type=form' % (property_id, act_window_dict['id'])
        return request.redirect(redirect_url)


    @http.route('/asset_property', type='json', method=['GET'], website=True)
    def get_property_asset(self, **kw):


        location = []
        product_id = http.request.env['product.product'].sudo().search([('is_property', '=', True), ('type', '=', 'property')])
        for rec in product_id:

            address = ""
            # if rec.street:
            #     address += rec.street + ","
            if rec.location:
                address += rec.location
            # if rec.city:
            #     address += rec.city + ","
            # if rec.zipcode != 0:
            #     address += str(rec.zipcode) + ","
            # if rec.state_id:
            #     address += str(rec.state_id.name) + ","
            # if rec.country_id:
            #     address += str(rec.country_id.name)
            # url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(address) + '?format=json'
            # response = requests.get(url).json()

            api_key = " AIzaSyCn-RXwAiHr8a4VSOCUV_a5eb65dA4Bssg"
            geo_url = 'https://maps.googleapis.com/maps/api/geocode/json?address='+address+"&key="+api_key
            response = requests.get(geo_url).json()
            state = dict(rec._fields['state'].selection).get(rec.state)


            property_book_for = dict(rec._fields['property_book_for'].selection).get(rec.property_book_for)
            if response['status'] == "OK" and state != 'Draft':
                for data in response['results']:
                    location_data = data['geometry']['location']
                    location.append({'state':state,
                                     'id': rec.id,
                                     'name':rec.name,
                                     'property_book_for': property_book_for,
                                     'lat': location_data['lat'],
                                     'lng': location_data['lng']
                                     })
                    break
        return location
