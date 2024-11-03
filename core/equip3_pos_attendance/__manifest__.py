# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS Attendance',
    'author': 'Hashmicro',
    'version': '1.1.5',
    'website': "https://www.hashmicro.com",
    'category': 'Human Resources/Attendances',
    'summary': """
    Check In / Check Out from POS After select Cashier
    """,
    'depends': ['web', 'pos_hr', 'hr_attendance', 'hr_attendance_base', 'hr_attendance_face_recognition', 'equip3_hr_attendance_extend',
        'point_of_sale','equip3_pos_general', 'equip3_pos_report'],
    'data': [
        'views/assets.xml',
        'views/hr_attendance_views.xml',
        'views/res_users_image_views.xml',
        'views/pos_config_views.xml',
    ],
    'qweb': [ 
        'static/src/xml/LoginScreen.xml',
        'static/src/xml/PosAttendanceButton.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
