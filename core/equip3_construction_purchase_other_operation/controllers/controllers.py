# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3ConstructionPurchaseOtherOperation(http.Controller):
#     @http.route('/equip3_construction_purchase_other_operation/equip3_construction_purchase_other_operation/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_construction_purchase_other_operation/equip3_construction_purchase_other_operation/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_construction_purchase_other_operation.listing', {
#             'root': '/equip3_construction_purchase_other_operation/equip3_construction_purchase_other_operation',
#             'objects': http.request.env['equip3_construction_purchase_other_operation.equip3_construction_purchase_other_operation'].search([]),
#         })

#     @http.route('/equip3_construction_purchase_other_operation/equip3_construction_purchase_other_operation/objects/<model("equip3_construction_purchase_other_operation.equip3_construction_purchase_other_operation"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_construction_purchase_other_operation.object', {
#             'object': obj
#         })
