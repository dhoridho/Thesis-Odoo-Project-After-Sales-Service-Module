import odoo
from odoo import http
from odoo.http import request
import datetime
from odoo.tools import pytz


class Website(http.Controller):

    def check_token_validity(self, token):
        kiosk_attendance_token = request.env['kiosk.attendance.token.log'].sudo().search([('token','=',token),('is_used','=',False)], limit=1, order='expired_date desc')
        if kiosk_attendance_token and datetime.datetime.now() < kiosk_attendance_token.expired_date:
            return {
                'valid': True,
                'kiosk_attendance_token': kiosk_attendance_token
            }
        return {
            'valid': False
        }

    @http.route('/kioskhrm', type='http', auth="public", website=True, csrf=False)
    def portal_kiosk_hrm(self, token=None, lat=None, long=None, location=None, **kw):
        values = {'employee_attendance': False}
        token_check = self.check_token_validity(token)
        if token_check['valid']:
            employee = request.env['hr.employee'].sudo().search([('user_id','=',token_check['kiosk_attendance_token'].user_id.id)], limit=1)
            if employee:
                if location:
                    active_location = request.env['active.location'].sudo().search([('employee_id','=',employee.id),('active_location_id.name','=',location)], limit=1)
                    employee.sudo().write({'selected_active_location_id': active_location.id})

                company = employee.company_id
                logo_url = '/web/image?model=res.company&id=%s&field=logo' % company.id
                values = { 
                    'token': token,
                    'employee_attendance': True,
                    'company_name': company.name,
                    'company_image_url': logo_url,
                    'lat': lat,
                    'long': long,
                }

        return request.render("equip3_hr_kiosk_web_attendance.portal_kiosk_hrm", values)

    @http.route('/kioskhrm/success/<token>/<int:attendance_id>', type='http', auth="public", website=True, csrf=False)
    def portal_kiosk_hrm_success(self, token, attendance_id, **kw):
        values = {'employee_attendance': False}
        token_check = self.check_token_validity(token)
        if token_check['valid']:
            attendance = request.env['hr.attendance'].sudo().search([('id','=',attendance_id)], limit=1)
            if attendance:
                user = request.env['res.users'].sudo().browse([2])
                timezone = pytz.timezone(user.tz) or pytz.utc
                attendance_check_in = pytz.utc.localize(attendance.check_in).astimezone(timezone).strftime("%H:%M:%S") if attendance.check_in else ''
                attendance_check_out = pytz.utc.localize(attendance.check_out).astimezone(timezone).strftime("%H:%M:%S") if attendance.check_out else ''

                hours_today = attendance.employee_id.hours_today
                hours_part = int(hours_today)
                minutes_part = int((hours_today - hours_part) * 60)
                hours_today_str = "%s hours, %s minutes" % (hours_part, minutes_part)

                values = {
                    'employee_attendance': True,
                    'employee_id': attendance.employee_id.id,
                    'employee_name': attendance.employee_id.name,
                    'employee_image_url': '/web/image?model=hr.employee&id=%s&field=image_1920' % attendance.employee_id.id,
                    'attendance_check_in_time': attendance_check_in,
                    'attendance_check_out_time': attendance_check_out,
                    'hours_today': hours_today_str,
                }
                
                if attendance.employee_id.attendance_state == 'checked_out':
                    values['attendance_check_out'] = True
                else:
                    values['attendance_check_out'] = False

                token_check['kiosk_attendance_token'].sudo().write({'is_used': True})

        return request.render("equip3_hr_kiosk_web_attendance.portal_kiosk_hrm_success", values)

    @http.route('/web/dataset/search_read', type='json', auth="public")
    def search_read(self, model, fields=False, offset=0, limit=False, domain=None, sort=None):
        return self.do_search_read(model, fields, offset, limit, domain, sort)

    def do_search_read(self, model, fields=False, offset=0, limit=False, domain=None, sort=None):
        Model = request.env[model]
        return Model.sudo().web_search_read(domain, fields, offset=offset, limit=limit, order=sort)

    @http.route('/hr_attendance_manual', auth='public', type="json")
    def hr_attendance_manual(self, **kw):
        employee_id = kw.get('employee_id')
        location = kw.get('location')
        webcam = kw.get('webcam')
        Employee = request.env['hr.employee'].sudo().browse(int(employee_id))

        return Employee.with_context(webcam=webcam).attendance_manual("", None, location)