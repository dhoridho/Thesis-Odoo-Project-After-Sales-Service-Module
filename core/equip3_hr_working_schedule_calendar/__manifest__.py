# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 HR Employee Working Calendar',
    'author': 'Hashmicro / Kumar',
    'website': 'https://www.hashmicro.com',
    'version': '1.2.2',
    'summary': 'Manage employee working schedule in Calendar view',
    'depends': ['resource', 'hr_contract', 'hr_attendance','equip3_hr_employee_access_right_setting','equip3_hr_working_schedule'],
    'category': 'Human Resources/Attendances',
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/employee_working_schedule_view.xml',
        'views/hr_generate_working_calendar_view.xml',
        'wizard/hr_working_schedule_calendar_import.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
