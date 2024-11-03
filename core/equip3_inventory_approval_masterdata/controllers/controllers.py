# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3InventoryApprovalMasterdata(http.Controller):
#     @http.route('/equip3_inventory_approval_masterdata/equip3_inventory_approval_masterdata/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_inventory_approval_masterdata/equip3_inventory_approval_masterdata/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_inventory_approval_masterdata.listing', {
#             'root': '/equip3_inventory_approval_masterdata/equip3_inventory_approval_masterdata',
#             'objects': http.request.env['equip3_inventory_approval_masterdata.equip3_inventory_approval_masterdata'].search([]),
#         })

#     @http.route('/equip3_inventory_approval_masterdata/equip3_inventory_approval_masterdata/objects/<model("equip3_inventory_approval_masterdata.equip3_inventory_approval_masterdata"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_inventory_approval_masterdata.object', {
#             'object': obj
#         })
