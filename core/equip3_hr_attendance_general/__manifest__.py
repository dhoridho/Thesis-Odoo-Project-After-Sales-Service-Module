# -*- coding: utf-8 -*-
{
   'name': 'HR Attendance General',
   'version': '1.1.4',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'HRM',
    'summary': """
    """,
   'depends': [
      'hr_attendance', 'hr_attendance_face_recognition'
   ],
   'data': [
       'assets/assets.xml',
   ],
   'qweb': [
        'static/src/xml/attendance.xml',
    ],
   'installable': True,
   'application': True,
   'auto_install': False,
}
