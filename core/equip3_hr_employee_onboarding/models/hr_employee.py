# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    onboarding_entry_checklist_ids = fields.One2many('employee.checklist.line', 'employee_id', string="Entry Checklist")
    onboarding_training_ids = fields.One2many('employee.training.line', 'employee_id', string="Training")
    onboarding_elearning_ids = fields.One2many('employee.elearning.line', 'employee_id', string="Elearning")
    offboarding_exit_checklist_ids = fields.One2many('employee.exit.checklist.line', 'employee_id', string="Exit Checklist")
    offboarding_exit_interview_ids = fields.One2many('employee.exit.interview.line', 'employee_id', string="Exit Interview")
    onboarding_progress = fields.Float(string='Onboarding Progress', default=0.0,
                                  help="Percentage of Onboarding Progress")
    offboarding_progress = fields.Float(string='Offboarding Progress', default=0.0,
                                 help="Percentage of Offboarding Progress")
    onboarding_inprogress = fields.Boolean('Onboarding in progress', compute='_compute_onboarding_inprogress', search='_search_onboarding_inprogress')
    offboarding_inprogress = fields.Boolean('Offboarding in progress', compute='_compute_offboarding_inprogress', search='_search_offboarding_inprogress')

    def _compute_onboarding_inprogress(self):
        onboardings = self.env['employee.orientation'].sudo().search([
            ('employee_name', 'in', self.ids),
            ('end_date_boarding', '>', date.today()),
            ('state', 'in', ('confirm'))
        ])
        onboarding_data = {}
        for onboarding in onboardings:
            onboarding_data[onboarding.employee_name.id] = {}
            onboarding_data[onboarding.employee_name.id]['current_onboarding_state'] = onboarding.state
        
        for employee in self:
            employee.onboarding_inprogress = onboarding_data.get(employee.id) and onboarding_data.get(employee.id, {}).get('current_onboarding_state') in ['confirm']
    
    def _search_onboarding_inprogress(self, operator, value):
        onboardings = self.env['employee.orientation'].sudo().search([
            ('employee_name', '!=', False),
            ('state', 'in', ['confirm']),
            ('end_date_onboarding', '>', date.today()),
        ])
        return [('id', 'in', onboardings.mapped('employee_name').ids)]
    
    def _compute_offboarding_inprogress(self):
        offboardings = self.env['employee.offboarding'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('end_date_offboarding', '>', date.today()),
            ('state', 'in', ('confirm'))
        ])
        offboarding_data = {}
        for offboarding in offboardings:
            offboarding_data[offboarding.employee_id.id] = {}
            offboarding_data[offboarding.employee_id.id]['current_offboarding_state'] = offboarding.state
        
        for employee in self:
            employee.onboarding_inprogress = offboarding_data.get(employee.id) and offboarding.get(employee.id, {}).get('current_offboarding_state') in ['confirm']
    
    def _search_offboarding_inprogress(self, operator, value):
        offboardings = self.env['employee.offboarding'].sudo().search([
            ('employee_id', '!=', False),
            ('state', 'in', ['confirm']),
            ('end_date_offboarding', '>', date.today()),
        ])
        return [('id', 'in', offboardings.mapped('employee_id').ids)]

class EmployeeChecklistLine(models.Model):
    _name = 'employee.checklist.line'
    _description = "Employee Checklist Line"

    employee_id = fields.Many2one('hr.employee', string="Employee", ondelete='cascade')
    line_id = fields.Many2one('onboarding.entry.checklist', string="Onboarding Checklist Line")
    name = fields.Char('Name')
    check = fields.Boolean('Check')

class EmployeeTrainingLine(models.Model):
    _name = 'employee.training.line'
    _description = "Employee Training Line"

    employee_id = fields.Many2one('hr.employee', string="Employee", ondelete='cascade')
    line_id = fields.Many2one('training.conduct', string="Onboarding Training Line")
    name = fields.Char('Name')
    check = fields.Boolean('Check')

class EmployeeElearningLine(models.Model):
    _name = 'employee.elearning.line'
    _description = "Employee Elearning Line"

    employee_id = fields.Many2one('hr.employee', string="Employee", ondelete='cascade')
    line_id = fields.Many2one('elearning.line', string="Onboarding Elearning Line")
    name = fields.Char('Name')
    check = fields.Boolean('Check')

class EmployeeExitChecklistLine(models.Model):
    _name = 'employee.exit.checklist.line'
    _description = "Employee Exit Checklist Line"

    employee_id = fields.Many2one('hr.employee', string="Employee", ondelete='cascade')
    line_id = fields.Many2one('offboarding.exit.checklist', string="Offboarding Exit Checklist Line")
    name = fields.Char('Name')
    check = fields.Boolean('Check')

class EmployeeExitInterviewLine(models.Model):
    _name = 'employee.exit.interview.line'
    _description = "Employee Exit Interview Line"

    employee_id = fields.Many2one('hr.employee', string="Employee", ondelete='cascade')
    line_id = fields.Many2one('offboarding.exit.interview', string="Offboarding Exit Interview Line")
    name = fields.Char('Name')
    check = fields.Boolean('Check')