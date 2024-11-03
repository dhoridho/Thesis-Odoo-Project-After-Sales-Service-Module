# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3HrEmployee(http.Controller):
#     @http.route('/equip3_hr_employee/equip3_hr_employee/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_hr_employee/equip3_hr_employee/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_hr_employee.listing', {
#             'root': '/equip3_hr_employee/equip3_hr_employee',
#             'objects': http.request.env['equip3_hr_employee.equip3_hr_employee'].search([]),
#         })

#     @http.route('/equip3_hr_employee/equip3_hr_employee/objects/<model("equip3_hr_employee.equip3_hr_employee"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_hr_employee.object', {
#             'object': obj
#         })
