{
    'name': 'Equip3 HR Philippines Restructure Menu',
    'version': '1.1.2',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'HRM PH',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['base', 'hr', 'hr_timesheet', 'hr_recruitment', 'hr_payroll_community', 'ohrms_overtime', 'survey', 'equip3_hashmicro_ui'],
    'data': [
        'views/human_resource_menu.xml',
        'views/category_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
