
{
    "name": "Financial Reports Group By Account Type",
    "version": "1.1.2",
    "license": "LGPL-3",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    'category': 'Accounting',
    "sequence": 1,
    "website": "http://www.serpentcs.com",
    "description": """
Singapore Financial Reports Group By Account Type.
----------------------------------------------------------------
This module is used to Filtered accounting financial reports and
grouped them by account type, sorted by sequence of account type.
""",
    'depends': ['sg_account_report'],
    'data': [
        'views/account_type_view.xml',
        'views/report_financial.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    "price": 39,
    "currency": 'EUR',
}
