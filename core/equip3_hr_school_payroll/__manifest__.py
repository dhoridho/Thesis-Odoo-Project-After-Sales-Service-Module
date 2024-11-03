{
    'name': 'Equip3 HR School Payroll',
    'version': '1.1.1',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'Uncategorized',
    'summary': """
    A module for payroll management in School
    """,
    'depends': ['base', 'hr_payroll_community'],
    'data': [
        'views/salary_rule.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
