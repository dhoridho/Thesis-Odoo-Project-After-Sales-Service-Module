# -*- coding: utf-8 -*-
# from odoo import http


# class IziSaleDiscountLine(http.Controller):
#     @http.route('/izi_sale_discount_line/izi_sale_discount_line/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/izi_sale_discount_line/izi_sale_discount_line/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('izi_sale_discount_line.listing', {
#             'root': '/izi_sale_discount_line/izi_sale_discount_line',
#             'objects': http.request.env['izi_sale_discount_line.izi_sale_discount_line'].search([]),
#         })

#     @http.route('/izi_sale_discount_line/izi_sale_discount_line/objects/<model("izi_sale_discount_line.izi_sale_discount_line"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('izi_sale_discount_line.object', {
#             'object': obj
#         })
