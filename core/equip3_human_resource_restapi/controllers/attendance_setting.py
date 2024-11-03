from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *
import pytz
from pytz import timezone


class Equip3HumanResourceRestAPIAttendanceSetting(RestApi):
    @route(['/api/employee/attendance_settings'],auth='user', type='http', methods=['get'])
    @authenticate
    def get_attendance_settings(self,**kw):  
        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        local = pytz.timezone(user_tz)
        now =  datetime.now(timezone(user_tz))
        now = now.replace(tzinfo=None)

        face_recognition_access = request.env['ir.config_parameter'].sudo().get_param('hr_attendance_face_recognition_access')
        face_recognition_store = request.env['ir.config_parameter'].sudo().get_param('hr_attendance_face_recognition_store')
        face_recognition_kiosk_auto = request.env['ir.config_parameter'].sudo().get_param('hr_attendance_face_recognition_kiosk_auto')
        auto_compare_face = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.auto_compare_face')
        auto_face_compare_time = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.auto_face_compare_time')
        attendance_range = request.env.user.partner_id.attendance_range
        work_calendar_employee = request.env['employee.working.schedule.calendar'].sudo().search([('employee_id','=',request.env.user.employee_id.id)]).filtered(lambda line:line.checkin.astimezone(local).replace(tzinfo=None).strftime("%Y-%m-%d") == now.strftime("%Y-%m-%d"))
        face_distance_limit = request.env['hr.config.settings'].sudo().search([],limit=1)

        
        response = {
            "checkin":datetime.strftime(work_calendar_employee[0].start_checkin.astimezone(local), '%Y-%m-%d %H:%M:%S')  if  work_calendar_employee else "-",
            "checkout":datetime.strftime(work_calendar_employee[0].end_checkout.astimezone(local), '%Y-%m-%d %H:%M:%S')  if work_calendar_employee else "-",
            'face_recognition_access':face_recognition_access,
            'face_recognition_store':face_recognition_store,
            'face_recognition_kiosk_auto':face_recognition_kiosk_auto,
            'auto_compare_face':auto_compare_face,
            'auto_face_compare_time':auto_face_compare_time,
            'amount_of_add_face_descriptor':request.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.amount_of_add_face_descriptor'),
            'attendance_range':attendance_range,
            'face_distance_limit':face_distance_limit.face_distance_limit,
            'active_location':[{
                'id':data.active_location_id.id,
                'name':data.active_location_id.name,
                                'latitude':data.active_location_id.partner_latitude,
                                'longitude':data.active_location_id.partner_longitude,
                                'attendance_range':data.active_location_id.attendance_range,
                                'is_default':data.is_default,
                                'is_use_att_reason':data.active_location_id.is_use_att_reason,
                                } for data in request.env.user.employee_id.active_location_ids]
            }
        return self.get_response(200, '200', {"code":200,
                                              "data":response
                                              })
    
    