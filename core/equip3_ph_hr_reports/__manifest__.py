{
    'name': 'Equip3 HR Report Philippines',
    'version': '1.1.6',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'HRM PH',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['hr_payroll_community','equip3_hr_payroll_general'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bir_form_1701_wizard_view.xml',
        'wizard/bir_form_2316_wizard_view.xml',
        'report/bir_form_1701_report.xml',
        'report/bir_form_1701_template.xml',
        'report/bir_form_2316_template.xml',
        'views/hr_salary_rule_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
