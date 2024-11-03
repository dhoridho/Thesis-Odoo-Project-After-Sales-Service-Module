# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from datetime import datetime, timedelta


class HrContractResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Auto Email Follow Cron
    auto_follow_up_salary_increment = fields.Boolean(config_parameter='equip3_hr_contract_extend.auto_follow_up_salary_increment')
    interval_number_salary_increment = fields.Integer(config_parameter='equip3_hr_contract_extend.interval_number_salary_increment')
    interval_type_salary_increment = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='',
        config_parameter='equip3_hr_contract_extend.interval_type_salary_increment')
    number_of_repetitions_salary_increment = fields.Integer(config_parameter='equip3_hr_contract_extend.number_of_repetitions_salary_increment')

    @api.onchange("interval_number_salary_increment")
    def _onchange_interval_number_salary_increment(self):
        if self.interval_number_salary_increment < 1:
            self.interval_number_salary_increment = 1

    @api.onchange("number_of_repetitions_salary_increment")
    def _onchange_number_of_repetitions_salary_increment(self):
        if self.number_of_repetitions_salary_increment < 1:
            self.number_of_repetitions_salary_increment = 1

    def set_values(self):
        super(HrContractResConfigSettings,self).set_values()
        cron_salary_increment_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Salary Increment Approver')])
        if self.auto_follow_up_salary_increment == True :
            if cron_salary_increment_approver:
                interval = self.interval_number_salary_increment
                delta_var = self.interval_type_salary_increment
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_salary_increment_approver.write({'interval_number':self.interval_number_salary_increment,'interval_type':self.interval_type_salary_increment,'nextcall':next_call,'active':True})
        else:
            if cron_salary_increment_approver:
                cron_salary_increment_approver.write({'active':False})