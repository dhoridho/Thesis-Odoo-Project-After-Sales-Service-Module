{
    "name": "Singapore OCBC Report",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["sg_hr_report"],
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "description": """
Singapore OCBC bank text file:
==============================================

Singapore ocbc bank text file generation :

* Generation of OCBC bank text file for salary payment.
""",
    "summary": """
Singapore OCBC bank text file:
""",
    "website": "http://www.serpentcs.com",
    "sequence": 1,
    "category": "Human Resources",
    'data': [
       'security/ir.model.access.csv',
       'wizard/ocbc_bank_specification_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    "price": 99,
    "currency": 'EUR',
}
