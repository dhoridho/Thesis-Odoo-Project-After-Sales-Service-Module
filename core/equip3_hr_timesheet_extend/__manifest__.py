# -*- coding: utf-8 -*-
{
    'name': "equip3_hr_timesheet_extend",
    'summary': "HR Timesheet Extend",
    'author': "Hashmicro",
    'website': "https://www.hashmicro.com",
    'category': 'Services/Timesheets',
    'version': '1.1.13',

    # any module necessary for this one to work correctly
    'depends': ['hr_timesheet','hr_timesheet_attendance','equip3_hr_payroll_extend_id','equip3_hashmicro_ui'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/hr_timesheet_security.xml',
        'data/hr_payroll_data.xml',
        'data/cron.xml',
        'data/mail.xml',
        'views/assets.xml',
        'views/hr_timesheet_menu.xml',
        'views/hr_timesheet_views.xml',
        'views/hr_manage_timesheet_views.xml',
        'views/res_config_settings_views.xml',
        'views/timesheet_approval_matrix_views.xml',
        'views/menu_category.xml',
        'wizard/timesheet_approval_matrix.xml',
        'views/hr_timesheet_flow.xml',
    ],
    'qweb': [
        "static/src/xml/timesheet_flow.xml",
    ],
}
