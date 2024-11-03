from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class Eequip3HrCareerTransitionResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    type_approval = fields.Selection([('employee_hierarchy','By Employee Hierarchy'),('approval_matrix','By Approval Matrix')],
                                     config_parameter='equip3_hr_career_transition.type_approval', default='employee_hierarchy')
    level = fields.Integer(config_parameter='equip3_hr_career_transition.level', default=1)
    send_by_wa_career_transition = fields.Boolean(config_parameter='equip3_hr_career_transition.send_by_wa_career_transition')
    send_by_email_career_transition = fields.Boolean(config_parameter='equip3_hr_career_transition.send_by_email_career_transition',
                                           default=True)
    # Auto Email Follow Cron
    auto_follow_up_career = fields.Boolean(config_parameter='equip3_hr_career_transition.auto_follow_up_career')
    interval_number_career = fields.Integer(config_parameter='equip3_hr_career_transition.interval_number_career')
    interval_type_career = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='', config_parameter='equip3_hr_career_transition.interval_type_career')
    number_of_repetitions_career = fields.Integer(
        config_parameter='equip3_hr_career_transition.number_of_repetitions_career')

    @api.onchange("level")
    def _onchange_level(self):
        if self.level < 1:
            self.level = 1
    
    @api.onchange("interval_number_career")
    def _onchange_interval_number_career(self):
        if self.interval_number_career < 1:
            self.interval_number_career = 1
    
    @api.onchange("number_of_repetitions_career")
    def _onchange_number_of_repetitions_career(self):
        if self.number_of_repetitions_career < 1:
            self.number_of_repetitions_career = 1

    def set_values(self):
        super(Eequip3HrCareerTransitionResConfigSettings,self).set_values()
        # Career
        cron_career_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Career Approver')])
        if self.auto_follow_up_career == True :
            if cron_career_approver:
                interval = self.interval_number_career
                delta_var = self.interval_type_career
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_career_approver.write({'interval_number':self.interval_number_career,'interval_type':self.interval_type_career,'nextcall':next_call,'active':True})
        else:
            if cron_career_approver:
                cron_career_approver.write({'active':False})