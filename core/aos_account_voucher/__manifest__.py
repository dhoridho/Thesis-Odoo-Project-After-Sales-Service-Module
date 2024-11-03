# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Account Voucher',
    'version': '1.2.11',
    'license': 'OPL-1',
    'summary': 'Account Voucher Management',
    'sequence': 1,
    "author": "Alphasoft",
    'description': """
Account Voucher
====================
    """,
    'category' : 'Account Voucher Management',
    'website': 'https://www.alphasoft.co.id/',
    'images':  ['images/main_screenshot.png'],
    'depends' : ['account', 'aos_base_account'],
    'data': [
        'security/account_voucher_security.xml',
        'security/ir.model.access.csv',
        'report/report_payment_voucher_template.xml',
        'report/report_payment_voucher.xml',
        'views/account_voucher_view.xml',
        'data/account_voucher_data.xml',
        'data/ir_sequence_data.xml',
    ],
    'demo': [],
    'test': [],
    'qweb': [],
    'css': [],
    'js': [],
    'price': 65.00,
    'currency': 'EUR',
    'installable': True,
    'application': False,
    'auto_install': False,
    #'post_init_hook': '_auto_install_l10n',
}
