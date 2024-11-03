{
    'name': 'Equip3 HR Employee Working Calendar Philippines',
    'version': '1.1.4',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'HRM PH',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['hr', 'hr_attendance', 'company_public_holidays_kanak'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_working_calendar_views.xml',
        'views/hr_generate_working_calendar_views.xml',
        'views/hr_shift_variation_views.xml',
        'views/menu.xml',
        "views/resource_calendar_views.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
