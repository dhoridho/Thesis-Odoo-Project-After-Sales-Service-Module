# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3InventoryConsignment(http.Controller):
#     @http.route('/equip3_inventory_consignment/equip3_inventory_consignment/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_inventory_consignment/equip3_inventory_consignment/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_inventory_consignment.listing', {
#             'root': '/equip3_inventory_consignment/equip3_inventory_consignment',
#             'objects': http.request.env['equip3_inventory_consignment.equip3_inventory_consignment'].search([]),
#         })

#     @http.route('/equip3_inventory_consignment/equip3_inventory_consignment/objects/<model("equip3_inventory_consignment.equip3_inventory_consignment"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_inventory_consignment.object', {
#             'object': obj
#         })
