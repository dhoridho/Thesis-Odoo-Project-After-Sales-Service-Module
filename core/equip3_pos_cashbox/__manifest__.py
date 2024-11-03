# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS Cashbox',
    'author': 'Hashmicro',
    'version': '1.1.12',
    'summary': 'POS POS Cashbox',
    'depends': ['account', 'equip3_pos_general'],
    'category': 'POS',
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/assets.xml',
        'views/account_bank_statement_views.xml',
        'views/product_views.xml',
        'views/pos_cash_views.xml',
        'views/pos_session_views.xml',
        'views/pos_config_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/cashbox_wizard_views.xml',
    ],
    'qweb': [
        'static/src/xml/PopUps/*.xml',
        'static/src/xml/ChromeWidgets/*.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}