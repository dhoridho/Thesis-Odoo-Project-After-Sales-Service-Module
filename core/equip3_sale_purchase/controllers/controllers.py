# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3SalePurchase(http.Controller):
#     @http.route('/equip3_sale_purchase/equip3_sale_purchase/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_sale_purchase/equip3_sale_purchase/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_sale_purchase.listing', {
#             'root': '/equip3_sale_purchase/equip3_sale_purchase',
#             'objects': http.request.env['equip3_sale_purchase.equip3_sale_purchase'].search([]),
#         })

#     @http.route('/equip3_sale_purchase/equip3_sale_purchase/objects/<model("equip3_sale_purchase.equip3_sale_purchase"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_sale_purchase.object', {
#             'object': obj
#         })
