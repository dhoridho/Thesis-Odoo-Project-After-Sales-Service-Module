# -*- coding: utf-8 -*-
# from odoo import http


# class PropertyRentalMgtAppModifierAsset(http.Controller):
#     @http.route('/property_rental_mgt_app_modifier_asset/property_rental_mgt_app_modifier_asset/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/property_rental_mgt_app_modifier_asset/property_rental_mgt_app_modifier_asset/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('property_rental_mgt_app_modifier_asset.listing', {
#             'root': '/property_rental_mgt_app_modifier_asset/property_rental_mgt_app_modifier_asset',
#             'objects': http.request.env['property_rental_mgt_app_modifier_asset.property_rental_mgt_app_modifier_asset'].search([]),
#         })

#     @http.route('/property_rental_mgt_app_modifier_asset/property_rental_mgt_app_modifier_asset/objects/<model("property_rental_mgt_app_modifier_asset.property_rental_mgt_app_modifier_asset"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('property_rental_mgt_app_modifier_asset.object', {
#             'object': obj
#         })
