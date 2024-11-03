# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3HrGeneralSetting(http.Controller):
#     @http.route('/equip3_hr_general_setting/equip3_hr_general_setting/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_hr_general_setting/equip3_hr_general_setting/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_hr_general_setting.listing', {
#             'root': '/equip3_hr_general_setting/equip3_hr_general_setting',
#             'objects': http.request.env['equip3_hr_general_setting.equip3_hr_general_setting'].search([]),
#         })

#     @http.route('/equip3_hr_general_setting/equip3_hr_general_setting/objects/<model("equip3_hr_general_setting.equip3_hr_general_setting"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_hr_general_setting.object', {
#             'object': obj
#         })
