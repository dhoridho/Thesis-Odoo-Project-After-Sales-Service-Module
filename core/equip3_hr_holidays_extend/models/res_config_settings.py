# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import datetime, timedelta

class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    connector_id = fields.Many2one('acrux.chat.connector', config_parameter='equip3_hr_holidays_extend.connector_id')
    send_by_wa = fields.Boolean(config_parameter='equip3_hr_holidays_extend.send_by_wa')
    send_by_email = fields.Boolean(config_parameter='equip3_hr_holidays_extend.send_by_email', default=True)
    # Auto Email Follow Cron
    auto_follow_up_leave = fields.Boolean(config_parameter='equip3_hr_holidays_extend.auto_follow_up_leave')
    interval_number_leave = fields.Integer(config_parameter='equip3_hr_holidays_extend.interval_number_leave')
    interval_type_leave = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='',
        config_parameter='equip3_hr_holidays_extend.interval_type_leave')
    number_of_repetitions_leave = fields.Integer(
        config_parameter='equip3_hr_holidays_extend.number_of_repetitions_leave')

    @api.onchange("interval_number_leave")
    def _onchange_interval_number_leave(self):
        if self.interval_number_leave < 1:
            self.interval_number_leave = 1

    @api.onchange("number_of_repetitions_leave")
    def _onchange_number_of_repetitions_leave(self):
        if self.number_of_repetitions_leave < 1:
            self.number_of_repetitions_leave = 1

    @api.model
    def get_values(self):
        res = super(ResConfigSettingsInherit, self).get_values()
        res.update(send_by_email=self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_email'))
        res.update(send_by_wa=self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_wa'))
        return res
    
    def set_values(self):
        super(ResConfigSettingsInherit, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_holidays_extend.send_by_email', self.send_by_email)
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_holidays_extend.send_by_wa', self.send_by_wa)
        # Leave Approve
        cron_leave_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Leave Approver')])
        if self.auto_follow_up_leave:
            if cron_leave_approver:
                interval = self.interval_number_leave
                delta_var = self.interval_type_leave
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_leave_approver.write(
                    {'interval_number': self.interval_number_leave, 'interval_type': self.interval_type_leave,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_leave_approver:
                cron_leave_approver.write({'active': False})
        # Leave Cancel Approve
        cron_leave_cancel_approver = self.env['ir.cron'].sudo().search(
            [('name', '=', 'Auto Follow Up Leave Cancel Approver')])
        if self.auto_follow_up_leave:
            if cron_leave_cancel_approver:
                interval = self.interval_number_leave
                delta_var = self.interval_type_leave
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_leave_cancel_approver.write(
                    {'interval_number': self.interval_number_leave, 'interval_type': self.interval_type_leave,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_leave_cancel_approver:
                cron_leave_cancel_approver.write({'active': False})
        # Leave Allocation Approve
        cron_leave_allocation_approver = self.env['ir.cron'].sudo().search(
            [('name', '=', 'Auto Follow Up Leave Allocation Approver')])
        if self.auto_follow_up_leave:
            if cron_leave_allocation_approver:
                interval = self.interval_number_leave
                delta_var = self.interval_type_leave
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_leave_allocation_approver.write(
                    {'interval_number': self.interval_number_leave, 'interval_type': self.interval_type_leave,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_leave_allocation_approver:
                cron_leave_allocation_approver.write({'active': False})
