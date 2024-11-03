# -*- coding: utf-8 -*-
# Copyright 2019 Artem Shurshilov
# Odoo Proprietary License v1.0

# This software and associated files (the "Software") may only be used (executed,
# modified, executed after modifications) if you have purchased a valid license
# from the authors, typically via Odoo Apps, or if you have received a written
# agreement from the authors of the Software (see the COPYRIGHT file).

# You may develop Odoo modules that use the Software as a library (typically
# by depending on it, importing it and using its resources), but without copying
# any source code or material from the Software. You may distribute those
# modules under the license of your choice, provided that this license is
# compatible with the terms of the Odoo Proprietary License (For example:
# LGPL, MIT, or proprietary licenses similar to this one).

# It is forbidden to publish, distribute, sublicense, or sell copies of the Software
# or modified copies of the Software.

# The above copyright notice and this permission notice must be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from odoo import http
from odoo.http import request
import werkzeug
from werkzeug import url_encode

from odoo.addons.hr_attendance_base.controllers.controllers import HrAttendanceBase


class HrAttendanceWebcam(HrAttendanceBase):
    @http.route('/login_kiosk', type='http', auth='none', methods=['GET'], csrf=False)
    def login_kiosk(self, login, password, db=None, force='', mod_file=None, **kw):
        if db and db != request.db:
            raise Exception(_("Could not select database '%s'") % db)
        uid = request.session.authenticate(request.db, login, password)
        url = '/web#%s' % url_encode({'action': 'hr_attendance_kiosk_mode'})
        return werkzeug.utils.redirect(url)

    @http.route('/hr_attendance_base', auth='user', type="json")
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
                employee_user_id = kw.get('employee')['user_id'] if kw.get('employee') else False

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
                images_ids = request.env['res.users.image'].search(
                    [('res_user_id', '=', request.env.user.id), ('descriptor', '!=', False)])
                descriptor_ids = images_ids.mapped('descriptor')
                labels_ids = images_ids.mapped('res_user_id.name')

                # get emotion gender age
                user_id = request.env['res.users'].browse(request.env.user.id)

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
