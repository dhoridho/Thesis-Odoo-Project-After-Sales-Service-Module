# -*- coding: utf-8 -*-

{
    'name': 'Xendit Payment Acquirer',
    'category': 'Accounting/Payment',
    'summary': 'Payment Acquirer: Xendit Implementation',
    'version': '1.1.1',
    'author': 'Kelvzxu',
    'license': 'GPL-3',
    'website': 'https://www.kltech-intl.com',
    'live_test_url' :  'https://www.youtube.com/watch?v=HoJJTBefz1A',
    'description': """Xendit Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'data/payment_icon_data.xml',
        'views/payment_views.xml',
        'data/payment_acquirer_data.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'price': 45.00,
    'currency': 'EUR',
    'post_init_hook': 'create_missing_journal_for_acquirers',

}
