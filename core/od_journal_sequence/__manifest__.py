# -*- coding: utf-8 -*-

{
    'name': 'Journal Sequence For Odoo 14',
    'version': '1.1.5',
    'category': 'Accounting',
    'summary': 'Journal Sequence For Odoo 14',
    'description': 'Journal Sequence For Odoo 14',
    'sequence': '1',
    'author': 'Odoo Developers',
    'support': 'developersodoo@gmail.com',
    'live_test_url': 'https://www.youtube.com/watch?v=z-xZwCah7wM',
    'depends': ['account'],
    'demo': [],
    'data': [
        'data/account_data.xml',
        'views/account_journal.xml',
        'views/account_move.xml',
    ],
    'qweb': [],
    'license': 'OPL-1',
    'price': 11,
    'currency': 'USD',
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
