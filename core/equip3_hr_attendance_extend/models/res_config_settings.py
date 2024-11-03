# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_status = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('leave', 'Leave')],
                                         string='Default Attendance Status', readonly=False, config_parameter='equip3_hr_attendance_extend.attendance_status')
    attendance_approval_matrix = fields.Boolean(config_parameter='equip3_hr_attendance_extend.attendance_approval_matrix', default=False)
    attendance_type_approval = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')], default='employee_hierarchy',
        config_parameter='equip3_hr_attendance_extend.attendance_type_approval')
    attendance_level = fields.Integer(config_parameter='equip3_hr_attendance_extend.attendance_level', default=1)
    attendance_validation = fields.Boolean(config_parameter='equip3_hr_attendance_extend.attendance_validation')
    send_by_wa_attendance = fields.Boolean(config_parameter='equip3_hr_attendance_extend.send_by_wa_attendance')
    send_by_mail_attendance = fields.Boolean(config_parameter='equip3_hr_attendance_extend.send_by_mail_attendance',
                                           default=True)
    # Auto Email Follow Cron
    auto_follow_up_attendance = fields.Boolean(config_parameter='equip3_hr_attendance_extend.auto_follow_up_attendance')
    interval_number_attendance = fields.Integer(config_parameter='equip3_hr_attendance_extend.interval_number_attendance')
    interval_type_attendance = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='',
        config_parameter='equip3_hr_attendance_extend.interval_type_attendance')
    number_of_repetitions_attendance = fields.Integer(
        config_parameter='equip3_hr_attendance_extend.number_of_repetitions_attendance')
    amount_of_add_face_descriptor = fields.Integer(default=3, config_parameter='equip3_hr_attendance_extend.amount_of_add_face_descriptor')
    update_attendance_status_limit =  fields.Integer(default=7, config_parameter='equip3_hr_attendance_extend.update_attendance_status_limit')
    past_date_limit = fields.Integer(default=0, config_parameter='equip3_hr_attendance_extend.past_date_limit')
    auto_compare_face = fields.Boolean(config_parameter='equip3_hr_attendance_extend.auto_compare_face', default=True)
    auto_face_compare_time = fields.Integer(default=0, config_parameter='equip3_hr_attendance_extend.auto_face_compare_time')


    @api.onchange("attendance_level")
    def _onchange_attendance_level(self):
        if self.attendance_level < 1:
            self.attendance_level = 1

    @api.onchange("interval_number_attendance")
    def _onchange_interval_number_attendance(self):
        if self.interval_number_attendance < 1:
            self.interval_number_attendance = 1

    @api.onchange("number_of_repetitions_attendance")
    def _onchange_number_of_repetitions_attendance(self):
        if self.number_of_repetitions_attendance < 1:
            self.number_of_repetitions_attendance = 1

    @api.onchange("auto_face_compare_time")
    def _onchange_auto_face_compare_time(self):
        if self.auto_face_compare_time < 0:
            raise ValidationError(_("Please only use an Integer value for Auto Compare Face Contour Field"))

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(auto_compare_face=self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.auto_compare_face'),
                   send_by_mail_attendance=self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_mail_attendance'))
        return res
    
    def set_values(self):
        super(ResConfigSettings,self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_attendance_extend.auto_compare_face', self.auto_compare_face)
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_attendance_extend.send_by_mail_attendance', self.send_by_mail_attendance)
        # Attendance
        cron_attendance_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Attendance Approver')])
        if self.auto_follow_up_attendance == True :
            if cron_attendance_approver:
                interval = self.interval_number_attendance
                delta_var = self.interval_type_attendance
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_attendance_approver.write({'interval_number':self.interval_number_attendance,'interval_type':self.interval_type_attendance,'nextcall':next_call,'active':True})
        else:
            if cron_attendance_approver:
                cron_attendance_approver.write({'active':False})
        # Working Schedule
        cron_working_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Working Approver')])
        if self.auto_follow_up_attendance == True:
            if cron_working_approver:
                interval = self.interval_number_attendance
                delta_var = self.interval_type_attendance
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_working_approver.write({'interval_number': self.interval_number_attendance, 'interval_type': self.interval_type_attendance, 'nextcall': next_call, 'active': True})
        else:
            if cron_working_approver:
                cron_working_approver.write({'active': False})