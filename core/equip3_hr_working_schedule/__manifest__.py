# -*- coding: utf-8 -*-
{
    'name': "Equip3 HR Employee Working Schedule",
    'author': 'HashMicro / Kumar',
    'summary': 'Manage Working Schedule with some types (Fixed Schedule, Shift Schedule and Roster Schedule)',
    'website': 'https://www.hashmicro.com',
    'category': 'Human Resources/Attendances',
    'version': '1.2.6',
    'depends': [
        'hr_contract',
        'resource',
        'branch'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/mass_update.xml',
        'views/resource.xml',
        'views/hr_attendance_formula_views.xml',
        'views/hr_shift_variation_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
