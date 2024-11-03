# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'HR Employee Travel Expense in Odoo ',
    'version': '1.1.5',
    'category': 'human resources',
    'summary': 'Apps for Hr Travel Expense Travel Expense reimbursement Employee Travel Expenses for Employee Travel Request for Employee Expenses Travel Expense voucher employee Travel expense Advance HR Travel Expense request HR Expenses of travel HR Expenses request',
    'description': """Employee Travel and Travel Expense Manage 
	
	Employee Travel Management and Expense Management
This module will allow you to manage travel of your employees and expense advance and submit expense claim.
Travel Expense reimbursement
employee Travel Expense reimbursement
employee Travel reimbursement in Odoo
employee reimbursement
Created Menus :
Employee Travel and Travel Expense

Travel/Travel Request
Travel/Travel Request/Employee Travel Request
Travel/Travel Request/Travel Requests To Approve
Defined Reports
HR Employee Travel Expenses
Employee Travel Expenses
Travel Expenses
Expenses of travel
employee Travel
Travel Expense voucher
travel voucher
Travel Request
Employee Travel Expenses
Travel Expenses
Employee Expenses

	
	""",
	
	
	
	
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.in',
    "price": 30,
    "currency": 'EUR',
    'depends': ['base','hr','hr_expense','project','equip3_hr_employee_access_right_setting'],
    'data': ['security/ir.model.access.csv',
            # 'security/groups.xml',
            'views/travel_request_views.xml',
            'report/employee_travel_report.xml',
            'report/report_views.xml',],
    'installable': True,
    'auto_install': False,
    'application': True,
    "live_test_url":'https://youtu.be/a7dVapF2ihw',
    "images":["static/description/Banner.png"],
}
