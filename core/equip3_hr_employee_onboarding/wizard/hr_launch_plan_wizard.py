# -*- coding: utf-8 -*-
from odoo import api, fields, models

class HrLaunchPlanWizard(models.TransientModel):
    _name = 'hr.launch.plan.wizard'
    _description = 'Launch Plan Wizard'

    plan = fields.Selection([('onboarding','Onboarding'),('offboarding','Offboarding')], string="Plan", default='onboarding', required=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        default=lambda self: self.env.context.get('active_id', None),
    )

    def action_launch(self):
        if self.plan == "onboarding":
            exist_onboarding = self.env['employee.orientation'].search([('employee_name','=',self.employee_id.id)],limit=1,order="id desc")
            description = ""
            if exist_onboarding:
                if exist_onboarding.total_current_entry_weight < exist_onboarding.total_entry_weightage:
                    description = "This employee's onboarding process is already underway. Do you want to create a new onboarding process? (If so, the current record will be removed.)"
                elif exist_onboarding.total_current_entry_weight == exist_onboarding.total_entry_weightage:
                    description = "This employee has finished their onboarding process. Do you want to create a new onboarding process? (If so, the current record will be removed.)"
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'hr.onboarding.offboarding.wizard',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'name': "Confirmation",
                    'target': 'new',
                    'context':{'default_employee_id':self.employee_id.id,'default_plan':'onboarding','default_description':description},
                }
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'employee.orientation',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'name': "Employee Onboarding",
                    'target': 'new',
                    'context':{'default_employee_name':self.employee_id.id},
                }
        else:
            exist_offboarding = self.env['employee.offboarding'].search([('employee_id','=',self.employee_id.id)],limit=1,order="id desc")
            description = ""
            if exist_offboarding:
                if exist_offboarding.total_current_exit_weight < exist_offboarding.total_exit_weightage:
                    description = "This employee's offboarding process is already underway. Do you want to create a new offboarding process? (If so, the current record will be removed.)"
                elif exist_offboarding.total_current_exit_weight == exist_offboarding.total_exit_weightage:
                    description = "This employee has finished their offboarding process. Do you want to create a new offboarding process? (If so, the current record will be removed.)"
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'hr.onboarding.offboarding.wizard',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'name': "Confirmation",
                    'target': 'new',
                    'context':{'default_employee_id':self.employee_id.id,'default_plan':'offboarding','default_description':description},
                }
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'employee.offboarding',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'name': "Employee Offboarding",
                    'target': 'new',
                    'context':{'default_employee_id':self.employee_id.id},
                }

class HrOnboardingOffboardingWizard(models.TransientModel):
    _name = 'hr.onboarding.offboarding.wizard'
    _description = 'HR Onboarding Offboarding Confirmation Wizard'

    plan = fields.Selection([('onboarding','Onboarding'),('offboarding','Offboarding')], string="Plan", required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    description = fields.Text('Description')

    def action_confirm(self):
        if self.plan == "onboarding":
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'employee.orientation',
                'view_type': 'form',
                'view_mode': 'form',
                'name': "Employee Onboarding",
                'target': 'new',
                'context':{'default_employee_name':self.employee_id.id},
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'employee.offboarding',
                'view_type': 'form',
                'view_mode': 'form',
                'name': "Employee Offboarding",
                'target': 'new',
                'context':{'default_employee_id':self.employee_id.id},
            }