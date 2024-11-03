# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3ApprovalHierarchy(http.Controller):
#     @http.route('/equip3_approval_hierarchy/equip3_approval_hierarchy/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_approval_hierarchy/equip3_approval_hierarchy/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_approval_hierarchy.listing', {
#             'root': '/equip3_approval_hierarchy/equip3_approval_hierarchy',
#             'objects': http.request.env['equip3_approval_hierarchy.equip3_approval_hierarchy'].search([]),
#         })

#     @http.route('/equip3_approval_hierarchy/equip3_approval_hierarchy/objects/<model("equip3_approval_hierarchy.equip3_approval_hierarchy"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_approval_hierarchy.object', {
#             'object': obj
#         })
