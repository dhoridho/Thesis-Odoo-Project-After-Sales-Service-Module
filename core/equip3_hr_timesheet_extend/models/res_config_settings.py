# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from datetime import datetime, timedelta

class HrOvertimeResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    timesheet_approval_method = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')],
        config_parameter='equip3_hr_timesheet_extend.timesheet_approval_method', default='employee_hierarchy')
    timesheet_approval_levels = fields.Integer(config_parameter='equip3_hr_timesheet_extend.timesheet_approval_levels', default=1)
    # Auto Email Follow Cron
    auto_follow_timesheet = fields.Boolean(config_parameter='equip3_hr_timesheet_extend.auto_follow_timesheet')
    interval_number_timesheet = fields.Integer(
        config_parameter='equip3_hr_timesheet_extend.interval_number_timesheet')
    interval_type_timesheet = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='',
        config_parameter='equip3_hr_timesheet_extend.interval_type_timesheet')
    number_of_repetitions_timesheet = fields.Integer(
        config_parameter='equip3_hr_timesheet_extend.number_of_repetitions_timesheet')

    @api.onchange("timesheet_approval_levels")
    def _onchange_approval_levels(self):
        if self.timesheet_approval_levels < 1:
            self.timesheet_approval_levels = 1

    @api.onchange("interval_number_timesheet")
    def _onchange_interval_number_timesheet(self):
        if self.interval_number_timesheet < 1:
            self.interval_number_timesheet = 1

    @api.onchange("number_of_repetitions_timesheet")
    def _onchange_number_of_repetitions_timesheet(self):
        if self.number_of_repetitions_timesheet < 1:
            self.number_of_repetitions_timesheet = 1

    @api.model
    def get_values(self):
        res = super(HrOvertimeResConfigSettings, self).get_values()
        res.update(timesheet_approval_method=self.env['ir.config_parameter'].sudo().get_param('equip3_hr_timesheet_extend.timesheet_approval_method',default='employee_hierarchy'))
        res.update(timesheet_approval_levels=self.env['ir.config_parameter'].sudo().get_param('equip3_hr_timesheet_extend.timesheet_approval_levels',default=1))
        return res

    def set_values(self):
        super(HrOvertimeResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_timesheet_extend.timesheet_approval_method', self.timesheet_approval_method)
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_timesheet_extend.timesheet_approval_levels', self.timesheet_approval_levels)
        cron_timesheet_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Timesheet Approver')])
        if self.auto_follow_timesheet == True:
            if cron_timesheet_approver:
                interval = self.interval_number_timesheet
                delta_var = self.interval_type_timesheet
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_timesheet_approver.write(
                    {'interval_number': self.interval_number_timesheet, 'interval_type': self.interval_type_timesheet,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_timesheet_approver:
                cron_timesheet_approver.write({'active': False})