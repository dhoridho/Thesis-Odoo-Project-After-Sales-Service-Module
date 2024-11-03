# -*- coding: utf-8 -*-

from odoo import fields, models

class HrEmployee(models.Model):
    _inherit = "hr.employee"
 
    def _in_pos_attendance_action_checked_in(self):
        self.ensure_one()

        #force check out
        webcam_check_in = self.env.context.get('webcam_snapshot')
        integrate_with_hr = self.env.context.get('integrate_with_hr')
        domain = [('employee_id', '=', self.id), ('check_out', '=', False)]
        if not integrate_with_hr:
            domain.append(('is_check_in_pos', '=', True))
        attendance = self.env['hr.attendance'].search(domain, limit=1)
        if attendance:
            vals = {'check_out': fields.Datetime.now()}
            if not integrate_with_hr:
                vals.update({'is_check_in_pos': True})
            attendance.write(vals)

        domain = [('employee_id', '=', self.id), ('check_out', '=', False)]
        if not integrate_with_hr:
            domain.append(('is_check_in_pos', '=', True))
        attendance = self.env['hr.attendance'].search(domain, limit=1)
        if not attendance:
            vals = {
                'employee_id': self.id,
                'check_in': fields.Datetime.now(),
                'webcam_check_in': webcam_check_in,
            }
            if not integrate_with_hr:
                vals.update({'is_check_in_pos': True})
            return self.env['hr.attendance'].create(vals)
        return attendance

    def _in_pos_attendance_action_checked_out(self):
        self.ensure_one()
        integrate_with_hr = self.env.context.get('integrate_with_hr')
        webcam_check_out = self.env.context.get('webcam_snapshot')
        domain = [('employee_id', '=', self.id), ('check_out', '=', False)]
        attendance = self.env['hr.attendance'].search(domain, limit=1)
        if attendance:
            vals = {
                'check_out': fields.Datetime.now(),
                'webcam_check_out': webcam_check_out
            }
            if not integrate_with_hr:
                vals.update({'is_check_in_pos': True})
            attendance.write(vals)
        return attendance
