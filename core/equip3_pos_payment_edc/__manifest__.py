# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS Payment EDC',
    'author': 'Hashmicro',
    'version': '1.1.7',
    'summary': 'Payment using EDC Device',
    'depends': ['equip3_pos_general'],
    'category': 'POS',
    'data': [
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/assets.xml',
        'views/pos_order_views.xml',
        'views/pos_payment_method_views.xml',
        'views/pos_payment_edc_views.xml',
    ],
    'qweb': [ 
        'static/src/xml/PopUps/*.xml',
        'static/src/xml/ChromeWidgets/*.xml',
        'static/src/xml/Screens/Payment/*.xml',
        'static/src/xml/Screens/Payment/PaymentScreen/*.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
