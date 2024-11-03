# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3HseAccessrightSetting(http.Controller):
#     @http.route('/equip3_hse_accessright_setting/equip3_hse_accessright_setting/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_hse_accessright_setting/equip3_hse_accessright_setting/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_hse_accessright_setting.listing', {
#             'root': '/equip3_hse_accessright_setting/equip3_hse_accessright_setting',
#             'objects': http.request.env['equip3_hse_accessright_setting.equip3_hse_accessright_setting'].search([]),
#         })

#     @http.route('/equip3_hse_accessright_setting/equip3_hse_accessright_setting/objects/<model("equip3_hse_accessright_setting.equip3_hse_accessright_setting"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_hse_accessright_setting.object', {
#             'object': obj
#         })
