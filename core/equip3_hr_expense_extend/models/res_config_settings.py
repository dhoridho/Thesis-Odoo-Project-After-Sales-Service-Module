from odoo import api, fields, models
from datetime import datetime, timedelta

class ExpenseResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expense_type_approval = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')], default='employee_hierarchy',
        config_parameter='equip3_hr_expense_extend.expense_type_approval')
    expense_level = fields.Integer(config_parameter='equip3_hr_expense_extend.expense_level', default=1)
    expense_reminder_before_days = fields.Integer(config_parameter='equip3_hr_expense_extend.expense_reminder_before_days')
    expense_choose_color_reminder = fields.Selection(
        [('red', 'Red'), ('green', 'Green'), ('blue', 'Blue'), ('purple', 'Purple'), ('yellow', 'Yellow'), ('white', 'White')],
        config_parameter='equip3_hr_expense_extend.expense_choose_color_reminder')
    send_by_wa_expense = fields.Boolean(config_parameter='equip3_hr_expense_extend.send_by_wa_expense')
    send_by_email_expense = fields.Boolean(config_parameter='equip3_hr_expense_extend.send_by_email_expense',
                                               default=True)
    auto_follow_up_expense = fields.Boolean(config_parameter='equip3_hr_expense_extend.auto_follow_up_expense')
    interval_number_expense = fields.Integer(config_parameter='equip3_hr_expense_extend.interval_number_expense')
    interval_type_expense = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')], default='',
        config_parameter='equip3_hr_expense_extend.interval_type_expense')
    number_of_repititions_expense = fields.Integer(config_parameter='equip3_hr_expense_extend.number_of_repititions_expense')
    expense_approval_matrix = fields.Boolean(
        default=False,
        config_parameter='equip3_hr_expense_extend.expense_approval_matrix'
    )

    @api.onchange("expense_level")
    def _onchange_expense_level(self):
        if self.expense_level < 1:
            self.expense_level = 1

    @api.onchange("interval_number_expense")
    def _onchange_interval_number_expense(self):
        if self.interval_number_expense < 1:
            self.interval_number_expense = 1

    @api.onchange("number_of_repititions_expense")
    def _onchange_number_of_repititions_expense(self):
        if self.number_of_repititions_expense < 1:
            self.number_of_repititions_expense = 1

    def set_values(self):
        super(ExpenseResConfigSettings,self).set_values()
        cron_expense_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Expense Approver')])
        if self.auto_follow_up_expense == True :
            if cron_expense_approver:
                interval = self.interval_number_expense
                delta_var = self.interval_type_expense
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_expense_approver.write({'interval_number':self.interval_number_expense,'interval_type':self.interval_type_expense,'nextcall':next_call,'active':True})
        else:
            if cron_expense_approver:
                cron_expense_approver.write({'active':False})