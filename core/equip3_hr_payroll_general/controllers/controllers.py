# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3HrPayrollGeneral(http.Controller):
#     @http.route('/equip3_hr_payroll_general/equip3_hr_payroll_general/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_hr_payroll_general/equip3_hr_payroll_general/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_hr_payroll_general.listing', {
#             'root': '/equip3_hr_payroll_general/equip3_hr_payroll_general',
#             'objects': http.request.env['equip3_hr_payroll_general.equip3_hr_payroll_general'].search([]),
#         })

#     @http.route('/equip3_hr_payroll_general/equip3_hr_payroll_general/objects/<model("equip3_hr_payroll_general.equip3_hr_payroll_general"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_hr_payroll_general.object', {
#             'object': obj
#         })
