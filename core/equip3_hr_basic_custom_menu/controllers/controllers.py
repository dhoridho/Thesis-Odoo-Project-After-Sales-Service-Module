# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3HrBasicCustomMenu(http.Controller):
#     @http.route('/equip3_hr_basic_custom_menu/equip3_hr_basic_custom_menu/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_hr_basic_custom_menu/equip3_hr_basic_custom_menu/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_hr_basic_custom_menu.listing', {
#             'root': '/equip3_hr_basic_custom_menu/equip3_hr_basic_custom_menu',
#             'objects': http.request.env['equip3_hr_basic_custom_menu.equip3_hr_basic_custom_menu'].search([]),
#         })

#     @http.route('/equip3_hr_basic_custom_menu/equip3_hr_basic_custom_menu/objects/<model("equip3_hr_basic_custom_menu.equip3_hr_basic_custom_menu"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_hr_basic_custom_menu.object', {
#             'object': obj
#         })
