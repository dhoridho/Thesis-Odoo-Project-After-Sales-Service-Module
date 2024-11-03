from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class Equip3HrTrainingResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    training_approval_matrix = fields.Boolean(config_parameter='equip3_hr_training.training_approval_matrix', default=False)
    training_type_approval = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')],
        config_parameter='equip3_hr_training.training_type_approval', default='employee_hierarchy')
    training_level = fields.Integer(config_parameter='equip3_hr_training.training_level', default=1)
    send_by_wa_training = fields.Boolean(config_parameter='equip3_hr_training.send_by_wa_training')
    send_by_email_training = fields.Boolean(config_parameter='equip3_hr_training.send_by_email_training', default=True)
    # Auto Email Follow Cron
    auto_follow_up_training = fields.Boolean(config_parameter='equip3_hr_training.auto_follow_up_training')
    interval_number_training = fields.Integer(config_parameter='equip3_hr_training.interval_number_training')
    interval_type_training = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='',
        config_parameter='equip3_hr_training.interval_type_training')
    number_of_repetitions_training = fields.Integer(
        config_parameter='equip3_hr_training.number_of_repetitions_training')

    @api.onchange("training_level")
    def _onchange_level(self):
        if self.training_level < 1:
            self.training_level = 1

    @api.onchange("interval_number_training")
    def _onchange_interval_number_training(self):
        if self.interval_number_training < 1:
            self.interval_number_training = 1

    @api.onchange("number_of_repetitions_training")
    def _onchange_number_of_repetitions_training(self):
        if self.number_of_repetitions_training < 1:
            self.number_of_repetitions_training = 1

    def set_values(self):
        super(Equip3HrTrainingResConfigSettings,self).set_values()
        # Training req
        cron_training_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Training Approver')])
        if self.auto_follow_up_training:
            if cron_training_approver:
                interval = self.interval_number_training
                delta_var = self.interval_type_training
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_training_approver.write({'interval_number':self.interval_number_training,'interval_type':self.interval_type_training,'nextcall':next_call,'active':True})
        else:
            if cron_training_approver:
                cron_training_approver.write({'active':False})
        # Training Cancellation
        cron_training_cancellation_approver = self.env['ir.cron'].sudo().search(
            [('name', '=', 'Auto Follow Up Training Cancellation Approver')])
        if self.auto_follow_up_training:
            if cron_training_cancellation_approver:
                interval = self.interval_number_training
                delta_var = self.interval_type_training
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_training_cancellation_approver.write(
                    {'interval_number': self.interval_number_training, 'interval_type': self.interval_type_training,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_training_cancellation_approver:
                cron_training_cancellation_approver.write({'active': False})
        # Training Conduct
        cron_training_conduct_approver = self.env['ir.cron'].sudo().search(
            [('name', '=', 'Auto Follow Up Training Conduct Approver')])
        if self.auto_follow_up_training:
            if cron_training_conduct_approver:
                interval = self.interval_number_training
                delta_var = self.interval_type_training
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_training_conduct_approver.write(
                    {'interval_number': self.interval_number_training, 'interval_type': self.interval_type_training,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_training_conduct_approver:
                cron_training_conduct_approver.write({'active': False})
        # Training Conduct Cancellation
        cron_training_conduct_cancellation_approver = self.env['ir.cron'].sudo().search(
            [('name', '=', 'Auto Follow Up Training Conduct Cancellation Approver')])
        if self.auto_follow_up_training:
            if cron_training_conduct_cancellation_approver:
                interval = self.interval_number_training
                delta_var = self.interval_type_training
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_training_conduct_cancellation_approver.write(
                    {'interval_number': self.interval_number_training, 'interval_type': self.interval_type_training,
                     'nextcall': next_call, 'active': True})
        else:
            if cron_training_conduct_cancellation_approver:
                cron_training_conduct_cancellation_approver.write({'active': False})