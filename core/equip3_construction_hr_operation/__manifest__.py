# -*- coding: utf-8 -*-
{
    'name': "Equip3 Construction HR Operation",

    'summary': """
        Manage your HR on the construction industry
    """,

    'description': """
        Manage your HR on the construction industry
    """,

    'author': "HashMicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Construction',
    'version': '1.1.13',

    # any module necessary for this one to work correctly
    'depends': ['base', 'equip3_construction_masterdata', 'hr', 'hr_timesheet','equip3_hr_masterdata_employee',
                'equip3_hr_payroll_extend_id', 'hr_attendance',
                'equip3_construction_operation', 'equip3_construction_sales_operation'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/construction_payroll_data.xml',
        'views/assets.xml',
        'views/hr_timesheet_view.xml',
        'views/project_view.xml',
        'views/progress_history_view.xml',
        'views/project_task_view.xml',
        'views/hr_employee.xml',
        'views/labour_cost_rate_view.xml',
        'views/hr_attendance_view.xml',
    ],

}
