{
    'name': 'Equip3 HR Payroll Philippines',
    'version': '1.1.4',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'HRM PH',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['hr_payroll_community'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_payroll_data.xml',
        'views/employee_payslip.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
