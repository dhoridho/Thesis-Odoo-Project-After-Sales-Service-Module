# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
###############################################################################

from odoo import models, api
from odoo.exceptions import ValidationError


class hr_expense(models.Model):
    _inherit = 'hr.expense'

    @api.model
    def create(self, vals):
        res = super(hr_expense, self).create(vals)
        # if res.employee_id and res.employee_id.sudo().employee_expense_line:
        #     for line in res.employee_id.sudo().employee_expense_line:
        #         if line.product_id == res.product_id and line.limit > 0 and line.limit < res.total_amount:
        #             list_data = ['Employee Expense limit exceeded \n \n']
        #             list_data.append('Employee Product = ' + '"' + str(line.product_id.name) + '"' + ', ' + 'limit = ' + '"' + str(line.limit) + '"' + ' is less then expense ' + '"' + str(
        #                 res.total_amount) + '"' + '\n')
        #             raise ValidationError((list_data))
        #         if not (line.product_id == res.product_id):
        #             if res.employee_id.department_id and res.employee_id.department_id.department_expense_line:
        #                 for dep_line in res.employee_id.department_id.department_expense_line:
        #                     if dep_line.product_id == res.product_id and dep_line.limit > 0 and dep_line.limit < res.total_amount:
        #                         list_data = ['Department Expense limit exceeded \n \n']
        #                         list_data.append(
        #                             'Department Product = ' + '"' + str(dep_line.product_id.name) + '"' + ', ' + 'limit = ' + '"' + str(dep_line.limit) + '"' + ' is less then expense ' + '"' + str(
        #                                 res.total_amount) + '"' + '\n')
        #                         raise ValidationError((list_data))
        # if not (res.employee_id.sudo().employee_expense_line) and res.employee_id.department_id and res.employee_id.department_id.department_expense_line:
        #     for dep_line in res.employee_id.department_id.department_expense_line:
        #         if dep_line.product_id == res.product_id and dep_line.limit > 0 and dep_line.limit < res.total_amount:
        #             list_data = ['Department Expense limit exceeded \n \n']
        #             list_data.append('Department Product = ' + '"' + str(dep_line.product_id.name) + '"' + ', ' + 'limit = ' + '"' + str(dep_line.limit) + '"' + ' is less then expense ' + '"' + str(
        #                 res.total_amount) + '"' + '\n')
        #             raise ValidationError((list_data))
        return res

    def write(self, vals):
        res = super(hr_expense, self).write(vals)
        # for exp in self:
        #     if exp.employee_id and exp.employee_id.sudo().employee_expense_line:
        #         for line in exp.employee_id.sudo().employee_expense_line:
        #             if line.product_id == exp.product_id and line.limit > 0 and line.limit < exp.total_amount:
        #                 list_data = ['Employee Expense limit exceeded \n \n']
        #                 list_data.append('Employee Product = ' + '"' + str(line.product_id.name) + '"' + ', ' + 'limit = ' + '"' + str(line.limit) + '"' + ' is less then expense ' + '"' + str(
        #                     exp.total_amount) + '"' + '\n')
        #                 raise ValidationError((list_data))
        #             if not (line.product_id == exp.product_id):
        #                 if exp.employee_id.department_id and exp.employee_id.department_id.department_expense_line:
        #                     for dep_line in exp.employee_id.department_id.department_expense_line:
        #                         if dep_line.product_id == exp.product_id and dep_line.limit > 0 and dep_line.limit < exp.total_amount:
        #                             list_data = ['Department Expense limit exceeded \n \n']
        #                             list_data.append('Department Product = ' + '"' + str(dep_line.product_id.name) + '"' + ', ' + 'limit = ' + '"' + str(
        #                                 dep_line.limit) + '"' + ' is less then expense ' + '"' + str(exp.total_amount) + '"' + '\n')
        #                             raise ValidationError((list_data))
        #     if not (exp.employee_id.sudo().employee_expense_line) and exp.employee_id.department_id and exp.employee_id.department_id.department_expense_line:
        #         for dep_line in exp.employee_id.department_id.department_expense_line:
        #             if dep_line.product_id == exp.product_id and dep_line.limit > 0 and dep_line.limit < exp.total_amount:
        #                 list_data = ['Department Expense limit exceeded \n \n']
        #                 list_data.append(
        #                     'Department Product = ' + '"' + str(dep_line.product_id.name) + '"' + ', ' + 'limit = ' + '"' + str(dep_line.limit) + '"' + ' is less then expense ' + '"' + str(
        #                         exp.total_amount) + '"' + '\n')
        #                 raise ValidationError((list_data))
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: