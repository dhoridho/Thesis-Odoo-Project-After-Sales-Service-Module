# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2021-today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################
{
    'name': "Construction Management System",
    'author': 'Ascetic Business Solution',
    'category': 'Purchases',
    'summary': """Construction Management""",
    'website': 'http://www.asceticbs.com',
    'description': """ """,
    'version': '1.1.6',
    'depends': ['base','purchase', 'hr_payroll_community','hr_timesheet_attendance'],
    'data': [
             'security/construction_security.xml',
             'security/ir.model.access.csv',
             'wizard/create_purchase_order_view.xml',
             'views/job_cost_sheet_view.xml',
             'views/project_view.xml',
             'views/material_view.xml',
             'views/employee_view.xml',
             'views/project_note_view.xml',
             'views/project_issues.xml',
             'views/job_order_view.xml',
             'views/job_note_view.xml',
             'views/issue_type.xml',
             'views/equipment_request_view.xml',
             'views/vehicle_request_view.xml',
             #'views/project_analysis_report_view.xml',
             'report/report_job_cost_sheet_view.xml',
             'report/report_job_cost_sheet_template.xml',
             'report/report_job_order_view.xml',
             'report/report_job_order_template.xml',
             'report/report_project_issue_view.xml',
             'report/report_project_issue_template.xml',
             'report/report_equipment_request_view.xml',
             'report/report_equipment_request_template.xml',
             'report/report_vehicle_request_view.xml',
             'report/report_vehicle_request_template.xml',
            #  'data/demo_product_view.xml',
             ],
    'live_test_url' : "http://www.test.asceticbs.com/web/database/selector",
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'price': 120.00,
    'currency': "EUR",
    'installable': True,
    'application': True,
    'auto_install': False,
}
