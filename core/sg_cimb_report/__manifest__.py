{
    "name": "Singapore CIMB Report",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "sequence": 1,
    "depends": ["sg_hr_report"],
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "description": """
Singapore CIMB bank text file:
==============================================

Singapore cimb bank text file generation :

* Generation of CIMB bank text file for salary payment.
""",
    "summary": """
Singapore CIMB bank text file:
""",
    "category": "Human Resources",
    'data': [
       'security/ir.model.access.csv',
       'wizard/cimb_bank_text_file_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 49,
    "currency": 'EUR',
}
