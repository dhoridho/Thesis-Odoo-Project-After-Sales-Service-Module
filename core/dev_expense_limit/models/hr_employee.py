# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields


class employee_expense(models.Model):
    _name = 'employee.expense'
    _description = 'Expense of an Employee'

    product_id = fields.Many2one('product.product', string="Product")
    limit = fields.Float(string="Limit")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', string="Department")


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    employee_expense_line = fields.One2many('employee.expense', 'employee_id', string="Employee Expense Limit")


class hr_department(models.Model):
    _inherit = 'hr.department'

    department_expense_line = fields.One2many('employee.expense', 'department_id', string="Department Expense Limit")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: