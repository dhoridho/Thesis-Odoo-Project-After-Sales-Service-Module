from odoo import models, fields


class HrEmployeeFamilyInfo(models.Model):
    _name = 'hr.employee.family'
    _description = 'HR Employee Family'

    employee_id = fields.Many2one('hr.employee', string="Employee", help='Select corresponding Employee',
                                  invisible=1)
    relation_id = fields.Many2one('hr.employee.relation', string="Relation", help="Relationship with the employee")
    member_name = fields.Char(string='Name')
    member_contact = fields.Char(string='Contact No')
    birth_date = fields.Date(string="DOB")
    age = fields.Integer("Age")
    education = fields.Char("Education")
    occupation = fields.Char()
    city = fields.Char()
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')


class EmployeeRelationInfo(models.Model):
    _name = 'hr.employee.relation'
    name = fields.Char(string="Relationship", help="Relationship with thw employee")
