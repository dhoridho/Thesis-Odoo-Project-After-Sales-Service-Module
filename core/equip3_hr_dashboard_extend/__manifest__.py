# -*- coding: utf-8 -*-
{
    'name': "Equip3 HR Dashboard Extend",
    'summary': '',
    'description': '',
    'author': "HashMicro",
    'website': "https://www.hashmicro.com",
    'category': 'Human Resources',
    'version': '2.7.14',
    'depends': ['hr_reward_warning','sh_hr_dashboard','equip3_hr_attendance_overtime','bi_employee_travel_managment','equip3_hr_career_transition','hr_employee_loan','ks_dashboard_ninja', 'equip3_hr_recruitment_extend', 'equip3_hr_working_schedule_calendar'],
    'data': [
        # 'security/ir.model.access.csv',
        'data/hr_dashboard_data.xml',
        'data/scheduler.xml',
        'views/templates.xml',
        'views/hr_dashboard.xml',
        'views/menu.xml',
        'views/director_dashboard.xml',
        'views/hr_operational_dashboard.xml',
    ],
    'qweb': [
        "static/src/xml/director_dashboard.xml",
        "static/src/xml/hr_operational_dashboard.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
