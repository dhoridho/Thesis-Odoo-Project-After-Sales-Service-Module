# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Equip3 HR HR Kiosk Web Attendance',
    'version': '1.0.1',
    'author': 'Hashmicro',
    'website': "https://www.hashmicro.com",
    'category': 'Human Resources/Attendances',
    'depends': ['base','hr','hr_attendance','equip3_hr_attendance_extend','hr_attendance_face_recognition'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/kiosk_attendance_token_log_views.xml',
        'views/kioskhrm_template.xml',
    ],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}