# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3RoleCore(http.Controller):
#     @http.route('/equip3_role_core/equip3_role_core/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_role_core/equip3_role_core/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_role_core.listing', {
#             'root': '/equip3_role_core/equip3_role_core',
#             'objects': http.request.env['equip3_role_core.equip3_role_core'].search([]),
#         })

#     @http.route('/equip3_role_core/equip3_role_core/objects/<model("equip3_role_core.equip3_role_core"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_role_core.object', {
#             'object': obj
#         })
