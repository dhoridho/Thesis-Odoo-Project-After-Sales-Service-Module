{
    "name": "Singapore - DBS bank giro",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "sequence": 1,
    "author": "Serpent Consulting Services Pvt. Ltd.",
    'category': 'Accounting',
    "website": "http://www.serpentcs.com",
    "description": """
Singapore DBS bank giro file:
==============================================

Singapore dbs bank giro file generation :

* Generation of DBS bank giro file for salary payment.
""",
    "summary": """
Singapore DBS bank giro file
""",
    'depends': ['sg_hr_report'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_bank_view_extended.xml',
        'wizard/dbs_bank_specification_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    "price": 99,
    "currency": 'EUR',
}
