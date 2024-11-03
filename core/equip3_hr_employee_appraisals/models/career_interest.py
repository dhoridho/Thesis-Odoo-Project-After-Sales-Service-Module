from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime

class CareerInterest(models.Model):
    _name = 'employee.career.interest'

    @api.returns('self')
    def _get_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False
    
    @api.model
    def _domain_job_interest(self):
        return [('company_id','=',self.env.company.id)]

    current_manager_ids = fields.Many2many('hr.employee', 'current_manager_rel' ,string="Current Manager", readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee Id", readonly=True, default=_get_employee)
    department_id = fields.Many2one('hr.department',string="Department", readonly=True)
    job_interest = fields.Many2one('hr.job',string="Job Interest", required=True,domain=_domain_job_interest)
    description = fields.Char(string="Description", required=True)

    def custom_menu(self):
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_self_service') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'My Career Interest',
                'res_model': 'employee.career.interest',
                'view_mode': 'tree',
                'domain':[('create_uid','=',self.env.user.id)],
                }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'My Career Interest',
                'res_model': 'employee.career.interest',
                'view_mode': 'tree'
                }

    @api.onchange('job_interest')
    def _onchange_job_interest(self):
        self.department_id = self.job_interest.department_id
        self.current_manager_ids = self.job_interest.employee_ids

class Employee(models.Model):
    _inherit = 'hr.employee'

    career_plan_ids = fields.One2many('employee.career.interest', 'employee_id')
    

