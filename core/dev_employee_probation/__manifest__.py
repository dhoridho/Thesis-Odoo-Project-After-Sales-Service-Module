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
    'name': 'Employee Probation Management',
    'version': '1.1.2',
    'sequence': 1,
    'category': 'Generic Modules/Human Resources',
    'description':
        """
        This Module add below functionality into odoo

        1.Employee Probation\n
Before hiring new employees in the organization, we have to see whether this job is worth doing or not. So they have to be monitored for some time, so that we can know their abilities. And that's why we put new employees in probation period. Using this odoo application you can easily manage probation period of an employee. You can create probation document for particular employee and write reviews on the probation document of the employee so at the end of the probation period you can get a clear picture

Key Features
Create Probation document of an employee
Write multiple review on the probation document of an employee
You can also give rating from zero to 5 star in review
You can give any one of following in performance of employee in review:
Excellent
Good
Average
Poor
Worst
New security access rights :
Probation Manager
Probation HR
Probation Manager can create probation documents
Probation HR can approve the reviews on the employee's probation document
Probation document is directly linked with the employee screen, so you can easily navigate to the probation document of an employee from the employee screen itself
You can print probation document as PDF Report

Probation Document
Probation liked with the employee screen
Probation document printed as PDF Report



    """,
    'summary': 'odoo app manage Employee Probation Management, employee probation request, manager approve employee probation request,probation Document, employee probation review approval, employee probation hr process, employee probation performance, hr probation, hr employee probation expense, Probation Manager',
    'depends': ['hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/probation_sequence.xml',
        'views/main_menus_view.xml',
        'views/probation_view.xml',
        'views/employee_view.xml',
        'report/probation_report_template.xml',
        'report/probation_report_menu.xml',
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
    'price':19.0,
    'currency':'EUR',
    #'live_test_url':'https://youtu.be/A5kEBboAh_k',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
