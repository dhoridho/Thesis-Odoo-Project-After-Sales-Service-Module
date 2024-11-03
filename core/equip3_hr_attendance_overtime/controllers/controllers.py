# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3HrAttendanceOvertime(http.Controller):
#     @http.route('/equip3_hr_attendance_overtime/equip3_hr_attendance_overtime/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_hr_attendance_overtime/equip3_hr_attendance_overtime/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_hr_attendance_overtime.listing', {
#             'root': '/equip3_hr_attendance_overtime/equip3_hr_attendance_overtime',
#             'objects': http.request.env['equip3_hr_attendance_overtime.equip3_hr_attendance_overtime'].search([]),
#         })

#     @http.route('/equip3_hr_attendance_overtime/equip3_hr_attendance_overtime/objects/<model("equip3_hr_attendance_overtime.equip3_hr_attendance_overtime"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_hr_attendance_overtime.object', {
#             'object': obj
#         })
