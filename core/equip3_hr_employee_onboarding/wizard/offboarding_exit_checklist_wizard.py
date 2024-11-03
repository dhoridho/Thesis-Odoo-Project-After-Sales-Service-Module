# -*- coding: utf-8 -*-
from odoo import api, fields, models

class OffboardingExitChecklistWizard(models.TransientModel):
    _name = 'offboarding.exit.checklist.wizard'
    _description = 'Offboarding Entry Checklist Wizard'

    feedback = fields.Text('Feedback', required=True)
    offboard_exit_checklist_id = fields.Many2one('offboarding.exit.checklist', required=True,
                                        string="Offboarding Exit Checklist")
    
    def action_done(self):
        self.offboard_exit_checklist_id.feedback = self.feedback
        self.offboard_exit_checklist_id.state = 'completed'
        emp_checklist = self.env['employee.exit.checklist.line'].search([('line_id','=',self.offboard_exit_checklist_id.id),('employee_id','=',self.offboard_exit_checklist_id.emp_offboarding_id.employee_id.id)])
        if emp_checklist:
            emp_checklist.check = True