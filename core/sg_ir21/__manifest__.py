{
    "name": "SG IR21 Report",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "depends": ['sg_income_tax_report'],
    "sequence": 1,
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "category": "Report",
    "description": """
    Singapore Form IR21 report.
============================
    - Generate IR21 pdf file report
    """,
    "summary": """
Singapore Form IR21 report.
============================
    - Generate IR21 pdf file report
    """,
    "summary": """
Singapore Form IR21 report.
    """,
    "data": [
         'security/ir.model.access.csv',
         'views/res_company_extended_view.xml',
         'views/hr_employee_extended_view.xml',
         'wizard/form_ir21_wizard_report.xml',
         'report/ir21_report_view.xml',
         'report/report.xml',
     ],
    'installable': True,
    'auto_install': False,
    'application': False,
    "price": 99,
    "currency": 'EUR',
}
