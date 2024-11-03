# -*- coding: utf-8 -*-
from odoo import api, fields, models

class OnboardingEntryChecklistWizard(models.TransientModel):
    _name = 'onboarding.entry.checklist.wizard'
    _description = 'Onboarding Entry Checklist Wizard'

    feedback = fields.Text('Feedback', required=True)
    onboard_entry_checklist_id = fields.Many2one('onboarding.entry.checklist', required=True,
                                        string="Onboarding Entry Checklist")
    
    def action_done(self):
        self.onboard_entry_checklist_id.feedback = self.feedback
        self.onboard_entry_checklist_id.state = 'completed'
        emp_checklist = self.env['employee.checklist.line'].search([('line_id','=',self.onboard_entry_checklist_id.id),('employee_id','=',self.onboard_entry_checklist_id.emp_onboarding_id.employee_name.id)])
        if emp_checklist:
            emp_checklist.check = True