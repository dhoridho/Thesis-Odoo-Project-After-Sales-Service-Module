{
    "name": "Singapore Income Tax report",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["sg_hr_report"],
    "sequence": 1,
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "category": "Human Resources",
    "description": """
    Singapore Income Tax reports.
============================
    - IR8A and IR8S esubmission txt file reports
    singapore IRAS report
    Singapore ir8a report
    Singapore ir8s report
    """,
    "summary": """
Singapore Income Tax reports.
    """,
    'data': ['security/group.xml',
             'security/ir.model.access.csv',
             'views/res_company_view.xml',
             'views/sg_income_tax_view.xml',
             'views/ir8a_form_report_view.xml',
             'views/ir8s_form_report_view.xml',
             'views/sg_income_tax_report_menu.xml',
             'wizard/emp_ir8a_text_file_view.xml',
             'wizard/emp_ir8s_text_file_view.xml',
             ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 149,
    "currency": 'EUR',
}
