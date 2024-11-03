# -*- coding: utf-8 -*-

from odoo import fields, models
import datetime

class ResUsers(models.Model):
    _inherit = "res.users"

    # last_attendance_id = fields.Many2one('hr.attendance', related="employee_id.last_attendance_id")

    def is_require_check_in(self):
        self.ensure_one()
        vals = {
            'isRequireCheckIn': True,
            'userHaveFaceTables': any(self.res_users_image_ids.mapped('descriptor'))
        }
        if self.employee_id.last_attendance_id and self.employee_id.last_attendance_id.check_in:
            vals.update({
                'isRequireCheckIn': self.employee_id.last_attendance_id.check_in.strftime('%Y-%m-%d') < fields.Datetime.now().strftime('%Y-%m-%d')
            })
        return vals

    def action_pos_attendance_checked_in(self):
        self.ensure_one()
        employee = self.employee_id
        if employee:
            if employee.user_id:
                modified_attendance = employee.with_user(employee.user_id)._in_pos_attendance_action_checked_in()
            else:
                modified_attendance = employee._in_pos_attendance_action_checked_in()
        return [self.id]


    def action_pos_attendance_checked_out(self):
        self.ensure_one()
        for employee in self.employee_ids:
            if employee.user_id:
                modified_attendance = employee.with_user(employee.user_id)._in_pos_attendance_action_checked_out()
            else:
                modified_attendance = employee._in_pos_attendance_action_checked_out() 
        return self.employee_ids

    def action_change_cashier(self, selected_cashier_id):
        self.ensure_one()
        selected_cashier = self.browse(selected_cashier_id)
        self.action_pos_attendance_checked_out()
        selected_cashier.action_pos_attendance_checked_in()

    def in_pos_action_check_in_out(self):
        context = self._context
        user = self.env['res.users'].search([('id', '=', context['employee']['user_id'])], limit=1)
        if user:
            employee = user.employee_id
            checkin_vals = {
                'employee_id': employee.id,
                'check_in': fields.Datetime.now(),
                # 'is_check_in_pos': True,
                # 'face_recognition_auto': context.get('face_recognition_auto', False),
                # 'webcam_snapshot': context.get('webcam_snapshot', False),
                # 'face_recognition_image': context.get('face_recognition_image', False),
            }
            #force check out
            domain = [('employee_id', '=', employee.id), ('check_out', '=', False)]
            attendance = self.env['hr.attendance'].search(domain, limit=1)
            if attendance:
                attendance.write({
                    'check_out': fields.Datetime.now()
                })

            #check in
            domain = [('employee_id', '=', employee.id), ('check_out', '=', False)]
            attendance = self.env['hr.attendance'].search(domain, limit=1)
            if not attendance:
                self.env['hr.attendance'].create(checkin_vals)

        return [user and user.id or False]
