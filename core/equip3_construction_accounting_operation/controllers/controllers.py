# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3ConstructionAccountingOperation(http.Controller):
#     @http.route('/equip3_construction_accounting_operation/equip3_construction_accounting_operation/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_construction_accounting_operation/equip3_construction_accounting_operation/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_construction_accounting_operation.listing', {
#             'root': '/equip3_construction_accounting_operation/equip3_construction_accounting_operation',
#             'objects': http.request.env['equip3_construction_accounting_operation.equip3_construction_accounting_operation'].search([]),
#         })

#     @http.route('/equip3_construction_accounting_operation/equip3_construction_accounting_operation/objects/<model("equip3_construction_accounting_operation.equip3_construction_accounting_operation"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_construction_accounting_operation.object', {
#             'object': obj
#         })
