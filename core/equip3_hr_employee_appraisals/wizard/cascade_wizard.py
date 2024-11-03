from typing import Sequence
from odoo import fields,models,api,_
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class equp3EmployeePerformanceCascadePopupWizard(models.TransientModel):
    _name = 'performance.cascade.wizard'
    
    
    performance_line_id = fields.Many2one('employee.performances.line')
    kpi_id = fields.Many2one('gamification.goal.definition',related='performance_line_id.name')
    weightage = fields.Float(related='performance_line_id.weightage')
    kpi_target = fields.Float(related='performance_line_id.kpi_target')
    line_ids = fields.One2many('performance.cascade.line.wizard','parent_id')
    date_range_id = fields.Many2one('performance.date.range')
    
    
    @api.model
    def default_get(self, fields):
        res = super(equp3EmployeePerformanceCascadePopupWizard, self).default_get(fields)
        employee_ids = []
        my_employee = self.env.user.employee_id
        if my_employee:
            for child_record in my_employee.child_ids:
                employee_ids.append(child_record.id)
                child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
        line_ids = []
        kpi_ids = self.env['employee.performances.line'].search([('employee_id','in',employee_ids),('name','=',self.env.context.get('kpi_id')),('date_range_id','=',self.env.context.get('default_date_range_id'))])
        if kpi_ids:
            for data in kpi_ids:
                line_ids.append((0,0,{'employee_id':data.employee_id.id,'kpi_id':data.id}))
            res['line_ids'] = line_ids
        
        return res
    
    
  
    
    def submit(self):
        cascade_ids = []
        employee_ids = []
        for record in self.line_ids:
            employee_ids.append(record.employee_id.id)
            cascade_ids.append((0,0,{'employee_id':record.employee_id.id,
                                     'assign_weightage':record.assign_weightage,
                                     'performance_id':record.kpi_id.id
                                     
                                     }                                
                                ))
        if self.performance_line_id.cascade_line_ids:
            for line in self.performance_line_id.cascade_line_ids:
                self.performance_line_id.cascade_line_ids = [(2,line.id)]
        self.performance_line_id.cascade_line_ids = cascade_ids
        self.performance_line_id.cascade_employee_ids = [(6,0,employee_ids)]
        self.performance_line_id.is_cascade = True
    
    
    
    
class equp3EmployeePerformanceCascadePopupWizardLine(models.TransientModel):
    _name = 'performance.cascade.line.wizard'
    
    
    user_id = fields.Many2one('res.users', default=lambda self:self.env.user.id)
    parent_id = fields.Many2one('performance.cascade.wizard')
    employee_id = fields.Many2one('hr.employee')
    department_id = fields.Many2one('hr.department',related='employee_id.department_id')
    job_id = fields.Many2one('hr.job',related='employee_id.job_id')
    assign_weightage = fields.Integer()
    kpi_id = fields.Many2one('employee.performances.line')
    employee_domain_ids = fields.Many2many('hr.employee',compute='_compute_employee_domain_ids')
    kpi_domain_ids = fields.Many2many('employee.performances.line',compute='_compute_kpi_domain_ids')
    date_range_id = fields.Many2one('performance.date.range')
    
    
    @api.depends('employee_id')
    def _compute_kpi_domain_ids(self):
        for record in self:
            kpi_ids = []
            if record.employee_id:
                kpi = self.env['employee.performances.line'].search([('employee_id','=',record.employee_id.id),('date_range_id','=',record.date_range_id.id)])
                if kpi:
                    kpi_ids.extend(data.id for data in kpi) 
                record.kpi_domain_ids = [(6,0,kpi_ids)]
            else:
                record.kpi_domain_ids = []               
    
    
    
    
    
    
    
    @api.onchange('assign_weightage')
    def _onchange_assign_weightage(self):
        for record in self:
            if record.assign_weightage > 100:
                raise ValidationError("Assign Weightage cannot greater than 100")
    
    
    @api.depends('user_id')
    def _compute_employee_domain_ids(self):
        employee_ids = []
        my_employee = self.env.user.employee_id
        if my_employee:
            for child_record in my_employee.child_ids:
                employee_ids.append(child_record.id)
                child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            if employee_ids:
                self.employee_domain_ids = [(6,0,employee_ids)]
            else:
                self.employee_domain_ids =  False
        else:
            self.employee_domain_ids =  False
        
    
    
    
    
    
    