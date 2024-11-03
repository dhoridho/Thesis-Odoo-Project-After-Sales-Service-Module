# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3HrContractEsignature(http.Controller):
#     @http.route('/equip3_hr_contract_esignature/equip3_hr_contract_esignature/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_hr_contract_esignature/equip3_hr_contract_esignature/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_hr_contract_esignature.listing', {
#             'root': '/equip3_hr_contract_esignature/equip3_hr_contract_esignature',
#             'objects': http.request.env['equip3_hr_contract_esignature.equip3_hr_contract_esignature'].search([]),
#         })

#     @http.route('/equip3_hr_contract_esignature/equip3_hr_contract_esignature/objects/<model("equip3_hr_contract_esignature.equip3_hr_contract_esignature"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_hr_contract_esignature.object', {
#             'object': obj
#         })
