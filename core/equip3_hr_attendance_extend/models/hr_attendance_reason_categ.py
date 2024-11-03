from odoo import models, fields,api

class hrAttendanceReasonCateg(models.Model):
    _name = 'hr.attendance.reason.categ'
    _description = 'HR Attendance Reason Category'
    
    
    name = fields.Char('Category')
    company_id = fields.Many2one('res.company',default=lambda self:self.env.company.id)
    