from odoo import http, _
from odoo.http import request, route
from odoo.addons.equip3_school_portal.controllers.school_portal import SchoolPortal

class SchoolPortal(SchoolPortal):
    @http.route(['/attendance', '/attendance/<int:attendance_id>'], type='http', auth='user', website=True, method=['GET', 'POST'])
    def get_daily_attendance(self, attendance_id=None,**kw):
        if request.env.user.has_group('school.group_school_administration'):
            return super(SchoolPortal, self).get_daily_attendance(attendance_id=attendance_id, **kw)
        elif request.env.user.has_group('school.group_school_teacher'):
            if attendance_id:
                attendance_id = request.env['daily.attendance'].browse(attendance_id)
                if attendance_id.user_id != request.env.user:
                    return request.render('website.page_404')
                if request.httprequest.method == 'POST':
                    attendance_id.sudo().attendance_validate()
                    return request.redirect("/attendance")
                return request.render('equip3_school_portal.daily_attendance_form', {'attendance_id': attendance_id})
            else:
                employee_id = request.env['hr.employee'].search([('user_id', '=', request.env.user.id)], limit=1)
                teacher_id = request.env['school.teacher'].search([('employee_id', '=', employee_id.id)], limit=1)
                return request.render('equip3_school_portal.daily_attendance_list', {'attendance_ids': request.env['daily.attendance'].search([('user_id', '=', teacher_id.id)])})