# Copyright (C) Softhealer Technologies.

import re
import json
import odoo
# import requests
from odoo import http
from odoo.http import request
from odoo.addons.hr_attendance_face_recognition.controllers.controllers import HrAttendanceWebcam


class Website(http.Controller):

    @http.route('/get/face-descriptor-amount', type='http', auth="public", website=True, csrf=False)
    def get_face_descriptor_amount(self, menu_id=None, **post): 
        user_id = post.get('user_id')

        res_users_id_search = request.env['res.users'].sudo().search([('id','=',user_id)])
        current_res_users_image_amount = len(res_users_id_search.res_users_image_ids)
        res_users_image_amount = current_res_users_image_amount + 1
        amount_of_add_face_descriptor = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.amount_of_add_face_descriptor')

        response = {
            'status_code': 200,
            'status_desc': 'Success',
            'current_res_users_image_amount': current_res_users_image_amount,
            'res_users_image_amount': res_users_image_amount,
            'amount_of_add_face_descriptor': amount_of_add_face_descriptor,
        }

        return json.dumps(response)


    @http.route('/post/create-face-recognition-image', type='http', auth="public", website=True, csrf=False)
    def post_create_face_recognition_image(self, menu_id=None, **post):
        res_users_image_obj = request.env['res.users.image'].sudo()
        res_users_image_obj.create({
            'descriptor': post.get('descriptor'),
            'image_detection': post.get('image_detection'),
            'image': post.get('image'),
            'res_user_id': post.get('res_user_id'),
            'name': post.get('name'),
            'sequence': post.get('sequence')
        })

        response = {
            'status_code': 200,
            'status_desc': 'Success',
        }
        return json.dumps(response)


    @http.route('/get/active-location-data', type="json", auth='user')
    def get_active_location_data(self, **post):
        location_list = []
        if post.get('user_id'):
            HrEmployee = request.env['hr.employee'].search([('user_id','=', post['user_id'])], limit=1)
            for location in HrEmployee.active_location_ids:
                values = {'id': location.id, 'partner_name': location.active_location_id.name}
                if location.is_default:
                    location_list.insert(0, values)
                else:
                    location_list.append(values)
        return {
            'location_list': location_list,
        }

    @http.route('/get/all-active-location-data', type="json", auth='user')
    def get_all_active_location_data(self, **post):
        location_list = []
        employee_id = False
        if post.get('user_id'):
            HrEmployee = request.env['hr.employee'].search([('user_id','=', post['user_id'])], limit=1)
            employee_id = HrEmployee.id
            default_user_location = request.env['active.location'].search([('employee_id','=',HrEmployee.id),('is_default','=',True)], limit=1)
            if default_user_location:
                values = {'id': default_user_location.id, 'partner_name': default_user_location.active_location_id.name}
                location_list.append(values)

            ActiveLocation = request.env['active.location'].search([])
            for location in ActiveLocation:
                values = {'id': location.id, 'partner_name': location.active_location_id.name}
                location_list.append(values)

            # remove duplicate data
            location_list = {d['partner_name']: d for d in location_list}
            location_list = list(location_list.values())

        return {
            'location_list': location_list,
            'employee_id': employee_id
        }


class HrAttendanceExtend(HrAttendanceWebcam):
    @http.route('/hr_attendance_base', auth='public', type="json")
    def index(self, **kw):
        res = super(HrAttendanceWebcam, self).index(**kw)
        face_recognition_enable = request.env['ir.config_parameter'].sudo(
        ).get_param('hr_attendance_face_recognition_access')
        face_recognition_store = request.env['ir.config_parameter'].sudo(
        ).get_param('hr_attendance_face_recognition_store')
        face_recognition_kiosk_auto = request.env['ir.config_parameter'].sudo(
        ).get_param('hr_attendance_face_recognition_kiosk_auto')

        labels_ids_emp = []
        labels_ids = []

        if kw.get('face_recognition_mode') == 'kiosk':
            employee_id = kw.get('employee_id')
            user_id = kw.get('user_id')
            if user_id:
                user_id = request.env['res.users'].browse(user_id)
                images_ids = request.env['res.users.image'].sudo().search([('res_user_id', '=', user_id.id), ('descriptor', '!=', False)])
                descriptor_ids = images_ids.mapped('descriptor')
                for i in images_ids:
                    labels_ids.append(i.res_user_id.name + ',' + str(i.res_user_id.id))
                labels_ids_emp.append({
                    'id': user_id.employee_id.id,
                    'attendance_state': user_id.employee_id.attendance_state,
                    'name': user_id.employee_id.name,
                    'hours_today': user_id.employee_id.hours_today,
                    'user_id':  user_id.employee_id.user_id.id
                })
            elif employee_id:
                emp = request.env['hr.employee'].browse(employee_id)
                images_ids = request.env['res.users.image'].sudo().search([('res_user_id', '=', emp.user_id.id), ('descriptor', '!=', False)])
                descriptor_ids = images_ids.mapped('descriptor')
                for i in images_ids:
                    labels_ids.append(i.res_user_id.name + ',' + str(i.res_user_id.id))
                labels_ids_emp.append({
                    'id': emp.id,
                    'attendance_state': emp.attendance_state,
                    'name': emp.name,
                    'hours_today': emp.hours_today,
                    'user_id':  emp.user_id.id
                })
                user_id = emp.user_id
            else:
                images_ids = request.env['res.users.image'].sudo().search([('descriptor', '!=', False)])
                descriptor_ids = images_ids.mapped('descriptor')
                for i in images_ids:
                    labels_ids.append(i.res_user_id.name + ',' + str(i.res_user_id.id))
                for la in images_ids.mapped('res_user_id.id'):
                    # all employees for user
                    emps = request.env['hr.employee'].sudo().search([('user_id', '=', la)])
                    # only needs fields
                    for emp in emps:
                        # {"id": 1, "attendance_state": "checked_out", "name": "Artem Shurshilov", "hours_today": 10.362222222222222}
                        labels_ids_emp.append({
                            'id': emp.id,
                            'attendance_state': emp.attendance_state,
                            'name': emp.name,
                            'hours_today': emp.hours_today,
                            'user_id':  emp.user_id.id
                        })
                user_id = request.env['res.users'].browse(request.env.user.id)
        else:
            employee_from_kiosk = kw.get('employee_from_kiosk') if kw.get('employee_from_kiosk') else False
            # make change employee and current user
            if employee_from_kiosk:
                employee_id = kw.get('employee')['id'] if kw.get('employee') else False
                employee_user_id = kw.get('employee').get('user_id') if kw.get('employee') else False
                # TO DO send from kiosk mode
                # get images
                images_ids = request.env['res.users.image'].search(
                    [('res_user_id', '=', employee_user_id), ('descriptor', '!=', False)])
                descriptor_ids = images_ids.mapped('descriptor')
                for i in images_ids:
                    labels_ids.append(i.res_user_id.name + ',' + str(i.res_user_id.id))

                # get emotion gender age
                user_id = request.env['res.users'].browse(employee_user_id)

            # current user == employee
            else:
                # get images
                if kw.get('token_user_id'):
                    token_user_id = int(kw.get('token_user_id'))
                else:
                    token_user_id = request.env.user.id

                images_ids = request.env['res.users.image'].search(
                    [('res_user_id', '=', token_user_id), ('descriptor', '!=', False)])
                descriptor_ids = images_ids.mapped('descriptor')
                for i in images_ids:
                    labels_ids.append(i.res_user_id.name + ',' + str(i.res_user_id.id))
                emps = request.env['hr.employee'].sudo().search([('user_id', '=', token_user_id)])
                for emp in emps:
                    labels_ids_emp.append({
                        'id': emp.id,
                        'attendance_state': emp.attendance_state,
                        'name': emp.name,
                        'hours_today': emp.hours_today,
                        'user_id':  emp.user_id.id
                    })

                # get emotion gender age
                user_id = request.env['res.users'].browse(token_user_id)

        res.update({
            'face_recognition_enable': True if face_recognition_enable else False,
            'face_recognition_store': True if face_recognition_store else False,
            'face_recognition_auto': True if face_recognition_kiosk_auto else False,
            'descriptor_ids': descriptor_ids,
            'labels_ids': labels_ids,
            'labels_ids_emp': labels_ids_emp,
            'face_emotion': user_id.face_emotion,
            'face_gender': user_id.face_gender,
            'face_age': user_id.face_age,
        })
        return res