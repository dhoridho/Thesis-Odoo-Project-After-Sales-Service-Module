# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from datetime import datetime, timedelta


class HrOvertimeResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    overtime_approval_matrix = fields.Boolean(config_parameter='equip3_hr_attendance_overtime.overtime_approval_matrix', default=False)
    approval_method = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')],
        config_parameter='equip3_hr_attendance_overtime.approval_method', default='employee_hierarchy')
    approval_levels = fields.Integer(config_parameter='equip3_hr_attendance_overtime.approval_levels', default=1)

    overtime_rounding = fields.Boolean(config_parameter='equip3_hr_attendance_overtime.overtime_rounding', default=False)
    overtime_rounding_type = fields.Selection(
        [('round', 'Round'), ('round_up', 'Round-Up'), ('round_down', 'Round-Down')],
        config_parameter='equip3_hr_attendance_overtime.overtime_rounding_type', default='round')
    overtime_rounding_digit = fields.Integer(config_parameter='equip3_hr_attendance_overtime.overtime_rounding_digit')
    send_by_wa_overtimes = fields.Boolean(config_parameter='equip3_hr_attendance_overtime.send_by_wa_overtimes')
    send_by_mail_overtimes = fields.Boolean(config_parameter='equip3_hr_attendance_overtime.send_by_mail_overtimes',
                                           default=True)

    # Auto Email Follow Cron
    auto_follow_up_overtime = fields.Boolean(config_parameter='equip3_hr_attendance_overtime.auto_follow_up_overtime')
    interval_number_overtime = fields.Integer(config_parameter='equip3_hr_attendance_overtime.interval_number_overtime')
    interval_type_overtime = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='',
        config_parameter='equip3_hr_attendance_overtime.interval_type_overtime')
    number_of_repetitions_overtime = fields.Integer(
        config_parameter='equip3_hr_attendance_overtime.number_of_repetitions_overtime')

    @api.onchange("approval_levels")
    def _onchange_approval_levels(self):
        if self.approval_levels < 1:
            self.approval_levels = 1

    @api.onchange("interval_number_overtime")
    def _onchange_interval_number_overtime(self):
        if self.interval_number_overtime < 1:
            self.interval_number_overtime = 1

    @api.onchange("number_of_repetitions_overtime")
    def _onchange_number_of_repetitions_overtime(self):
        if self.number_of_repetitions_overtime < 1:
            self.number_of_repetitions_overtime = 1

    def set_values(self):
        super(HrOvertimeResConfigSettings,self).set_values()
        # Overtime
        cron_overtime_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Overtime Approver')])
        if self.auto_follow_up_overtime == True :
            if cron_overtime_approver:
                interval = self.interval_number_overtime
                delta_var = self.interval_type_overtime
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_overtime_approver.write({'interval_number':self.interval_number_overtime,'interval_type':self.interval_type_overtime,'nextcall':next_call,'active':True})
        else:
            if cron_overtime_approver:
                cron_overtime_approver.write({'active':False})
        #Actual Overtime
        cron_actual_overtime_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Actual Overtime Approver')])
        if self.auto_follow_up_overtime == True:
            if cron_actual_overtime_approver:
                interval = self.interval_number_overtime
                delta_var = self.interval_type_overtime
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_actual_overtime_approver.write(
                    {'interval_number': self.interval_number_overtime, 'interval_type': self.interval_type_overtime,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_actual_overtime_approver:
                cron_actual_overtime_approver.write({'active': False})