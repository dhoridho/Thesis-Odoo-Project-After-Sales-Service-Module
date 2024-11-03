# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3HrEmployeeDisciplinary(http.Controller):
#     @http.route('/equip3_hr_employee_disciplinary/equip3_hr_employee_disciplinary/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_hr_employee_disciplinary/equip3_hr_employee_disciplinary/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_hr_employee_disciplinary.listing', {
#             'root': '/equip3_hr_employee_disciplinary/equip3_hr_employee_disciplinary',
#             'objects': http.request.env['equip3_hr_employee_disciplinary.equip3_hr_employee_disciplinary'].search([]),
#         })

#     @http.route('/equip3_hr_employee_disciplinary/equip3_hr_employee_disciplinary/objects/<model("equip3_hr_employee_disciplinary.equip3_hr_employee_disciplinary"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_hr_employee_disciplinary.object', {
#             'object': obj
#         })
