# from attr import field
from odoo import models,api,fields


class nineBoxMatrixAnalysis(models.Model):
    _name = 'nine.box.analysis'
    _rec_name = 'matrix_id'
    
    evaluation_id = fields.Many2one('employee.performance')
    job_id = fields.Many2one('hr.job')
    employee_id = fields.Many2one('hr.employee')
    matrix_id = fields.Many2one('nine.box.matrix')