{
    'name': 'Equip3 HR School Payroll',
    'version': '1.1.1',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'Uncategorized',
    'summary': """
    A module for payroll management in School
    """,
    'depends': ['base', 'hr_payroll_community', 'equip3_hr_payroll_extend_id'],
    'data': [
        'views/salary_rule.xml',
        'views/hr_contract_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
