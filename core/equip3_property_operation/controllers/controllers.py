# -*- coding: utf-8 -*-
# from odoo import http


# class PropertyRentalMgtAppModifier(http.Controller):
#     @http.route('/property_rental_mgt_app_modifier/property_rental_mgt_app_modifier/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/property_rental_mgt_app_modifier/property_rental_mgt_app_modifier/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('property_rental_mgt_app_modifier.listing', {
#             'root': '/property_rental_mgt_app_modifier/property_rental_mgt_app_modifier',
#             'objects': http.request.env['property_rental_mgt_app_modifier.property_rental_mgt_app_modifier'].search([]),
#         })

#     @http.route('/property_rental_mgt_app_modifier/property_rental_mgt_app_modifier/objects/<model("property_rental_mgt_app_modifier.property_rental_mgt_app_modifier"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('property_rental_mgt_app_modifier.object', {
#             'object': obj
#         })
