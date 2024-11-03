# -*- coding: utf-8 -*-
# from odoo import http


# class PropertyRentalMgtAppModifierContract(http.Controller):
#     @http.route('/property_rental_mgt_app_modifier_contract/property_rental_mgt_app_modifier_contract/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/property_rental_mgt_app_modifier_contract/property_rental_mgt_app_modifier_contract/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('property_rental_mgt_app_modifier_contract.listing', {
#             'root': '/property_rental_mgt_app_modifier_contract/property_rental_mgt_app_modifier_contract',
#             'objects': http.request.env['property_rental_mgt_app_modifier_contract.property_rental_mgt_app_modifier_contract'].search([]),
#         })

#     @http.route('/property_rental_mgt_app_modifier_contract/property_rental_mgt_app_modifier_contract/objects/<model("property_rental_mgt_app_modifier_contract.property_rental_mgt_app_modifier_contract"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('property_rental_mgt_app_modifier_contract.object', {
#             'object': obj
#         })
