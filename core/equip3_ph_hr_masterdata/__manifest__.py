{
    'name': 'Equip3 HR Masterdata Philippines',
    'version': '1.1.1',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'HRM PH',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['hr'],
    'data': [
        'views/hr_employee_views.xml',
        'views/resource_calendar_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
