# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3GeneralProducts(http.Controller):
#     @http.route('/equip3_general_products/equip3_general_products/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_general_products/equip3_general_products/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_general_products.listing', {
#             'root': '/equip3_general_products/equip3_general_products',
#             'objects': http.request.env['equip3_general_products.equip3_general_products'].search([]),
#         })

#     @http.route('/equip3_general_products/equip3_general_products/objects/<model("equip3_general_products.equip3_general_products"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_general_products.object', {
#             'object': obj
#         })
