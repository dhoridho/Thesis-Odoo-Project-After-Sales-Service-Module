# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import datetime, timedelta


class Equip3HrRecruitmentExtendResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_sms = fields.Boolean(string="SMS", config_parameter='equip3_hr_recruitment_extend.is_sms')
    is_whatsapp = fields.Boolean(string="WA", config_parameter='equip3_hr_recruitment_extend.is_whatsapp')
    mpp = fields.Boolean(string="MPP", config_parameter='equip3_hr_recruitment_extend.mpp')
    mpp_approval_matrix = fields.Boolean(config_parameter='equip3_hr_recruitment_extend.mpp_approval_matrix', default=False)
    man_power_type_approval = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')],
        config_parameter='equip3_hr_recruitment_extend.man_power_type_approval', default='employee_hierarchy')
    man_power_level = fields.Integer(config_parameter='equip3_hr_recruitment_extend.man_power_level', default=2)
    connector_id = fields.Many2one('acrux.chat.connector',config_parameter='equip3_hr_recruitment_extend.connector_id')
    send_by_wa_recruitment = fields.Boolean(config_parameter='equip3_hr_recruitment_extend.send_by_wa')
    send_by_email_recruitment = fields.Boolean(config_parameter='equip3_hr_recruitment.send_by_email')
    limit_to_one_response_per_email_recruitment = fields.Boolean(config_parameter='equip3_hr_recruitment.limit_to_one_response_per_email_recruitment')
    range_time_number = fields.Integer(config_parameter='equip3_hr_recruitment.range_time_number', default=1)
    range_time_period = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('year', 'Year')
    ], config_parameter='equip3_hr_recruitment.range_time_period', default='year')
    is_email = fields.Boolean(config_parameter='equip3_hr_recruitment.is_email')
    is_id_card_number = fields.Boolean(config_parameter='equip3_hr_recruitment.is_id_card_number')
    is_phone_number = fields.Boolean(config_parameter='equip3_hr_recruitment.is_phone_number')
    max_apply_of_applicant = fields.Integer(config_parameter='equip3_hr_recruitment.max_apply_of_applicant')
    offering_letter_approval_matrix = fields.Boolean(config_parameter='equip3_hr_recruitment_extend.offering_letter_approval_matrix', default=False)
    offering_letter_approval_method = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')],
        config_parameter='equip3_hr_recruitment.offering_letter_approval_method', default='employee_hierarchy')
    offering_letter_approval_level = fields.Integer(config_parameter='equip3_hr_recruitment.offering_letter_approval_level', default=1)
    is_auto_next_stage_psychological = fields.Boolean(string="Auto Next Stage", default=False, config_parameter='equip3_hr_recruitment_extend.is_auto_next_stage_psychological')
    auto_completion_on_psychological = fields.Selection([('by_job_position', 'By Job Position'), ('by_psychological_test', 'By Psychological Test')], config_parameter='equip3_hr_recruitment_extend.auto_completion_on_psychological', default='by_job_position')
    # Auto Email Follow Cron
    auto_follow_recruitment = fields.Boolean(config_parameter='equip3_hr_recruitment_extend.auto_follow_recruitment')
    interval_number_recruitment = fields.Integer(config_parameter='equip3_hr_recruitment_extend.interval_number_recruitment')
    interval_type_recruitment = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='', config_parameter='equip3_hr_recruitment_extend.interval_type_recruitment')
    number_of_repetitions_recruitment = fields.Integer(config_parameter='equip3_hr_recruitment_extend.number_of_repetitions_recruitment')
    applicant_blacklist = fields.Boolean(config_parameter='equip3_hr_recruitment_extend.applicant_blacklist')
    bl_email = fields.Boolean(config_parameter='equip3_hr_recruitment_extend.bl_email')
    bl_id_card_number = fields.Boolean(config_parameter='equip3_hr_recruitment_extend.bl_id_card_number')
    bl_phone_number = fields.Boolean(config_parameter='equip3_hr_recruitment_extend.bl_phone_number')
    # is_cost_price_per_warehouse = fields.Boolean()
    
    @api.onchange('applicant_blacklist')
    def _onchange_applicant_blacklist(self):
        for data in self:
            if data.applicant_blacklist:
                data.bl_email = True
                data.bl_id_card_number = True
                data.bl_phone_number = True

    @api.onchange("man_power_level")
    def _onchange_man_power_level(self):
        if self.man_power_level < 1:
            self.man_power_level = 1
    
    @api.onchange("offering_letter_approval_level")
    def _onchange_offering_letter_approval_level(self):
        if self.offering_letter_approval_level < 1:
            self.offering_letter_approval_level = 1

    @api.onchange("interval_number_recruitment")
    def _onchange_interval_number_recruitment(self):
        if self.interval_number_recruitment < 1:
            self.interval_number_recruitment = 1

    @api.onchange("number_of_repetitions_emp_change")
    def _onchange_number_of_repetitions_recruitment(self):
        if self.number_of_repetitions_recruitment < 1:
            self.number_of_repetitions_recruitment = 1
    
    @api.model
    def set_values(self):
        super(Equip3HrRecruitmentExtendResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_recruitment_extend.limit_to_one_response_per_email_recruitment", self.limit_to_one_response_per_email_recruitment or False)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_recruitment_extend.range_time_number", self.range_time_number or False)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_recruitment_extend.range_time_period", self.range_time_period or False)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_recruitment_extend.is_email", self.is_email or False)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_recruitment_extend.is_id_card_number", self.is_id_card_number or False)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_recruitment_extend.is_phone_number", self.is_phone_number or False)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_recruitment_extend.max_apply_of_applicant", self.max_apply_of_applicant or False)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_recruitment_extend.offering_letter_approval_matrix", self.offering_letter_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_recruitment_extend.offering_letter_approval_method", self.offering_letter_approval_method)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_recruitment_extend.offering_letter_approval_level", self.offering_letter_approval_level)
        cron_recruitment = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Recruitment Change Request')])
        if self.auto_follow_recruitment == True:
            if cron_recruitment:
                interval = self.interval_number_recruitment
                delta_var = self.interval_type_recruitment
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_recruitment.write(
                    {'interval_number': self.interval_number_recruitment, 'interval_type': self.interval_type_recruitment,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_recruitment:
                cron_recruitment.write({'active': False})
