from odoo import api, fields, models
from datetime import datetime, timedelta


class TravelResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    travel_type_approval = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')],
        default='employee_hierarchy',
        config_parameter='equip3_hr_travel_extend.travel_type_approval')
    travel_level = fields.Integer(config_parameter='equip3_hr_travel_extend.travel_level', default=1)
    send_by_wa_travel = fields.Boolean(config_parameter='equip3_hr_travel_extend.send_by_wa_travel')
    send_by_email_travel = fields.Boolean(config_parameter='equip3_hr_travel_extend.send_by_email_travel', default=True)
    # Auto Email Follow Cron
    auto_follow_up_travel = fields.Boolean(config_parameter='equip3_hr_travel_extend.auto_follow_up_travel')
    interval_number_travel = fields.Integer(config_parameter='equip3_hr_travel_extend.interval_number_travel')
    interval_type_travel = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='',
        config_parameter='equip3_hr_travel_extend.interval_type_travel')
    number_of_repetitions_travel = fields.Integer(
        config_parameter='equip3_hr_travel_extend.number_of_repetitions_travel')
    travel_approval_matrix = fields.Boolean(
        default=False,
        config_parameter='equip3_hr_travel_extend.travel_approval_matrix'
    )
    update_attendance_status_travel_limit = fields.Integer(default=7, config_parameter='equip3_hr_travel_extend.update_attendance_status_travel_limit')
    

    @api.onchange("travel_level")
    def _onchange_travel_level(self):
        if self.travel_level < 1:
            self.travel_level = 1

    @api.onchange("interval_number_travel")
    def _onchange_interval_number_travel(self):
        if self.interval_number_travel < 1:
            self.interval_number_travel = 1

    @api.onchange("number_of_repetitions_travel")
    def _onchange_number_of_repetitions_travel(self):
        if self.number_of_repetitions_travel < 1:
            self.number_of_repetitions_travel = 1

    def set_values(self):
        super(TravelResConfigSettings,self).set_values()
        # TRavel Request
        cron_travel_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Travel Approver')])
        if self.auto_follow_up_travel == True :
            if cron_travel_approver:
                interval = self.interval_number_travel
                delta_var = self.interval_type_travel
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_travel_approver.write({'interval_number':self.interval_number_travel,'interval_type':self.interval_type_travel,'nextcall':next_call,'active':True})
        else:
            if cron_travel_approver:
                cron_travel_approver.write({'active':False})
        # TRavel Cancel Request
        cron_travel_cancel_approver = self.env['ir.cron'].sudo().search(
            [('name', '=', 'Auto Follow Up Travel Cancel Approver')])
        if self.auto_follow_up_travel == True:
            if cron_travel_cancel_approver:
                interval = self.interval_number_travel
                delta_var = self.interval_type_travel
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_travel_cancel_approver.write(
                    {'interval_number': self.interval_number_travel, 'interval_type': self.interval_type_travel,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_travel_cancel_approver:
                cron_travel_cancel_approver.write({'active': False})