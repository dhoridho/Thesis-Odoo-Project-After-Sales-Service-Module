{
    "name": "SG Letter Undertaking Report",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["base", 'sg_hr_report'],
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "sequence": 1,
    "website": "http://www.serpentcs.com",
    "category": "Report",
    "description": """
    Singapore Letter Undertaking report.
============================
    - Generate Letter Undertaking pdf file report
    employee undertaking report
    employee releaving process
    releaving letter
    """,
    "summary": """
Singapore Letter Undertaking report.
    """,
    "data": [
        'security/ir.model.access.csv',
        'wizard/wizard_letter_undertaking_view.xml',
        'report/sg_report.xml',
        'report/sg_report_letter_undertaking.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    "price": 29,
    "currency": 'EUR',
}
