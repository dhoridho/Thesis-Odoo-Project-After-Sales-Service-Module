from odoo import api, fields, models
from datetime import datetime, timedelta


class LoanResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    loan_approval_matrix = fields.Boolean(config_parameter='equip3_hr_employee_loan_extend.loan_approval_matrix', default=False)
    loan_type_approval = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')], default='employee_hierarchy',
        config_parameter='equip3_hr_employee_loan_extend.loan_type_approval')
    loan_level = fields.Integer(config_parameter='equip3_hr_employee_loan_extend.loan_level', default=1)
    send_by_wa_loan = fields.Boolean(config_parameter='equip3_hr_employee_loan_extend.send_by_wa_loan')
    send_by_email_loan = fields.Boolean(config_parameter='equip3_hr_employee_loan_extend.send_by_email_loan', default=True)
    loan_rounding = fields.Boolean(config_parameter='equip3_hr_employee_loan_extend.loan_rounding', default=False)
    loan_rounding_type = fields.Selection(
        [('round', 'Round'), ('round_up', 'Round-Up'), ('round_down', 'Round-Down')],
        config_parameter='equip3_hr_employee_loan_extend.loan_rounding_type', default='round')
    loan_rounding_digit = fields.Integer(config_parameter='equip3_hr_employee_loan_extend.loan_rounding_digit')
    # Auto Email Follow Cron
    auto_follow_up_loan = fields.Boolean(config_parameter='equip3_hr_employee_loan_extend.auto_follow_up_loan')
    interval_number_loan = fields.Integer(config_parameter='equip3_hr_employee_loan_extend.interval_number_loan')
    interval_type_loan = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='',
        config_parameter='equip3_hr_employee_loan_extend.interval_type_loan')
    number_of_repetitions_loan = fields.Integer(
        config_parameter='equip3_hr_employee_loan_extend.number_of_repetitions_loan')

    @api.onchange("loan_level")
    def _onchange_loan_level(self):
        if self.loan_level < 1:
            self.loan_level = 1

    @api.onchange("interval_number_loan")
    def _onchange_interval_number_loan(self):
        if self.interval_number_loan < 1:
            self.interval_number_loan = 1

    @api.onchange("number_of_repetitions_loan")
    def _onchange_number_of_repetitions_loan(self):
        if self.number_of_repetitions_loan < 1:
            self.number_of_repetitions_loan = 1

    def set_values(self):
        super(LoanResConfigSettings,self).set_values()
        #loan req
        cron_loan_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Loan Approver')])
        if self.auto_follow_up_loan == True :
            if cron_loan_approver:
                interval = self.interval_number_loan
                delta_var = self.interval_type_loan
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_loan_approver.write({'interval_number':self.interval_number_loan,'interval_type':self.interval_type_loan,'nextcall':next_call,'active':True})
        else:
            if cron_loan_approver:
                cron_loan_approver.write({'active':False})
        # loan Cancel
        cron_loan_cancel_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Loan Cancel Approver')])
        if self.auto_follow_up_loan == True:
            if cron_loan_cancel_approver:
                interval = self.interval_number_loan
                delta_var = self.interval_type_loan
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_loan_cancel_approver.write(
                    {'interval_number': self.interval_number_loan, 'interval_type': self.interval_type_loan,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_loan_cancel_approver:
                cron_loan_cancel_approver.write({'active': False})
        # Full loan Approver
        cron_full_loan_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Full Loan Approver')])
        if self.auto_follow_up_loan == True:
            if cron_full_loan_approver:
                interval = self.interval_number_loan
                delta_var = self.interval_type_loan
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_full_loan_approver.write(
                    {'interval_number': self.interval_number_loan, 'interval_type': self.interval_type_loan,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_full_loan_approver:
                cron_full_loan_approver.write({'active': False})