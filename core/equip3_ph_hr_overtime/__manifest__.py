{
    'name': 'Equip3 HR Overtime Philippines',
    'version': '1.1.1',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'HRM PH',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['hr', 'ohrms_overtime', 'hr_contract', 'equip3_ph_hr_payroll'],
    'data': [
        'data/hr_overtime_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
