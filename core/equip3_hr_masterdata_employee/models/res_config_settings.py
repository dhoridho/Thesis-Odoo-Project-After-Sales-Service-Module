# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import datetime, timedelta


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    emp_seq = fields.Boolean(string="Employee ID Sequence Number", default=True)
    # employee_change_request_approval_method = fields.Selection(
    #     [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')],
    #     config_parameter='equip3_hr_masterdata_employee.employee_change_request_approval_method', default='employee_hierarchy')
    # employee_change_request_approval_levels = fields.Integer(config_parameter='equip3_hr_masterdata_employee.employee_change_request_approval_levels', default=1)

    # @api.onchange("employee_change_request_approval_levels")
    # def _onchange_employee_change_request_approval_levels(self):
    #     if self.employee_change_request_approval_levels < 1:
    #         self.employee_change_request_approval_levels = 1

    # Auto Email Follow Cron
    auto_follow_emp_change = fields.Boolean(config_parameter='equip3_hr_masterdata_employee.auto_follow_emp_change')
    interval_number_emp_change = fields.Integer(config_parameter='equip3_hr_masterdata_employee.interval_number_emp_change')
    interval_type_emp_change = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='',
        config_parameter='equip3_hr_masterdata_employee.interval_type_emp_change')
    number_of_repetitions_emp_change = fields.Integer(
        config_parameter='equip3_hr_masterdata_employee.number_of_repetitions_emp_change')
    emp_change_req_approval_matrix = fields.Boolean(string='Employee Change Request Approval Matrix', config_parameter='equip3_hr_masterdata_employee.emp_change_req_approval_matrix')
    emp_change_req_approval_method = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')],
        config_parameter='equip3_hr_masterdata_employee.emp_change_req_approval_method', default='employee_hierarchy')
    emp_change_req_level = fields.Integer(config_parameter='equip3_hr_masterdata_employee.emp_change_req_level', default=1)
    #Salary Increment Setting
    salary_increment_approval_matrix = fields.Boolean(string='Salary Increment Approval Matrix', default=False, config_parameter='equip3_hr_masterdata_employee.salary_increment_approval_matrix')
    salary_increment_approval_method = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')],
        config_parameter='equip3_hr_masterdata_employee.salary_increment_approval_method', default='employee_hierarchy')
    salary_level = fields.Integer(config_parameter='equip3_hr_masterdata_employee.salary_level', default=1)


    @api.onchange("interval_number_emp_change")
    def _onchange_interval_number_emp_change(self):
        if self.interval_number_emp_change < 1:
            self.interval_number_emp_change = 1

    @api.onchange("number_of_repetitions_emp_change")
    def _onchange_number_of_repetitions_emp_change(self):
        if self.number_of_repetitions_emp_change < 1:
            self.number_of_repetitions_emp_change = 1

    def set_values(self):
        super(ResConfigSettingsInherit, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_masterdata_employee.emp_seq',
                                                         self.emp_seq or 'False')
        sequence_emp =  self.env['ir.sequence'].search([('code','=','hr.employee')],limit=1)
        if sequence_emp:
            sequence_emp.active = self.emp_seq
        # self.env['ir.config_parameter'].sudo().set_param('equip3_hr_masterdata_employee.timesheet_approval_method', self.employee_change_request_approval_method)
        # self.env['ir.config_parameter'].sudo().set_param('equip3_hr_masterdata_employee.timesheet_approval_levels', self.employee_change_request_approval_levels)
        cron_emp_change = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Employee Change Request')])
        if self.auto_follow_emp_change == True:
            if cron_emp_change:
                interval = self.interval_number_emp_change
                delta_var = self.interval_type_emp_change
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_emp_change.write(
                    {'interval_number': self.interval_number_emp_change, 'interval_type': self.interval_type_emp_change,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_emp_change:
                cron_emp_change.write({'active': False})

    @api.model
    def get_values(self):
        res = super(ResConfigSettingsInherit, self).get_values()
        res.update(emp_seq=False if self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.emp_seq') == "False" else True)  
        
                                                                         
        # res.update(employee_change_request_approval_method=self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.employee_change_request_approval_method',default='employee_hierarchy'))
        # res.update(employee_change_request_approval_levels=self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.employee_change_request_approval_levels',default=1))
        return res
