# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle 
#
##############################################################################

{
    'name': 'Employee Expense Limit',
    'version': '14.0.1.1.4',
    'sequence': 1,
    'category': 'Generic Modules/Human Resources',
    'description':
         """
              Odoo app to set Employee Expense Limit on employee profile
Employee Expense Limit

Odoo Employee Expense Limit

Manage Employee Expense Limit

Odoo manage Employee Expense Limit

Expense limit 

Odoo expense limit 

odoo application helping to set Employee expense limit

For Helping This module useful to set Employee expense limit.

Odoo For Helping This module useful to set Employee expense limit.

check Employee expense limit

Odoo check Employee expense limit

check Employee department Expense Limit

Odoo check Employee department Expense Limit

Employee expense sheet 

Odoo employee expense sheet 

Manage employee expense 

Odoo manage employee expense 

HR Expense 

Odoo HR Expense 

Manage HR Expense 

Odoo manage HR Expense 

HR Expense Form 

Odoo HR Expense Form 

Manage HR Expense Form

Odoo manage HR Expense Form 

Employee Department Expense Limit

Odoo Employee Department Expense Limit

Manage Employee Department Expense Limit

Odoo manage Employee Department Expense Limit

Helping This module useful to set Employee expense limit.

Odoo Helping This module useful to set Employee expense limit.

Employee expense limit

Odoo Employee expense limit

Manage Employee expense limit

Odoo Manage Employee expense limit

Employee department Expense Limit

Odoo Employee department Expense Limit

Manage Employee department Expense Limit

Odoo manage Employee department Expense Limit

Expense

Odoo Expense

Manage Expense

Odoo Manage Expense

Expense Limit

Odoo Expense Limit

Manage Expense Limit

Odoo Manage Expense Limit

Expense Form

Odoo Expense Form

Manage Expense Form

Odoo Manage Expense Form

Employee Department Expense Limit

Odoo Employee Department Expense Limit

Manage Employee Department Expense Limit

Odoo Manage Employee Department Expense Limit

         """,
    'summary': 'Odoo app to set Employee Expense Limit on employee profile based on each product, Expense Limit,Employee department Expense Limit,check Employee expense limit,Manage HR Expense Limit, Expense Limit warning, hr employee based Expense Limit',
    'depends': ['hr_expense'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_view.xml',
        'views/hr_department_view.xml'
    ],
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    
    # author and support Details =============#
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'website': 'http://www.devintellecs.com',    
    'maintainer': 'DevIntelle Consulting Service Pvt.Ltd', 
    'support': 'devintelle@gmail.com',
    'price':20.0,
    'currency':'EUR',
    #'live_test_url':'https://youtu.be/A5kEBboAh_k',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
