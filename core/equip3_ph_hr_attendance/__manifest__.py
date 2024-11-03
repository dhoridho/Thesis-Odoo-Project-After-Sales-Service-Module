{
    'name': 'Equip3 HR Attendance Philippines',
    'version': '1.1.3',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'HRM PH',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['hr', 'hr_attendance', 'hr_attendance_base', 'hr_attendance_face_recognition', 'equip3_ph_hr_working_calendar'],
    'data': [
        'views/hr_attendance_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
