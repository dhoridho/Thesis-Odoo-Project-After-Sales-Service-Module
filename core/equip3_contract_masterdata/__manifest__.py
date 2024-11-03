# -*- coding: utf-8 -*-
{
    'name': "Contract Master Data",
    'summary': "Contract Master Data",
    'description': "Contract Master Data",
    'author': "My Hashmicro",
    'website': "https://www.hashmicro.com",
    'category': 'Partner',
    'application': True,
    'version': '1.1.1',
    'depends': ['base', 'agreement', 'agreement_legal', 'account', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/agreement_view.xml',
        'wizard/create_agreement_wizard.xml',
    ],

    'installable': True,
    'auto_install': False,
}
