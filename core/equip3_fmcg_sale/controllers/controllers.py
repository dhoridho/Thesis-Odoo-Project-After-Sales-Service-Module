# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3FmcgSale(http.Controller):
#     @http.route('/equip3_fmcg_sale/equip3_fmcg_sale/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_fmcg_sale/equip3_fmcg_sale/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_fmcg_sale.listing', {
#             'root': '/equip3_fmcg_sale/equip3_fmcg_sale',
#             'objects': http.request.env['equip3_fmcg_sale.equip3_fmcg_sale'].search([]),
#         })

#     @http.route('/equip3_fmcg_sale/equip3_fmcg_sale/objects/<model("equip3_fmcg_sale.equip3_fmcg_sale"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_fmcg_sale.object', {
#             'object': obj
#         })
