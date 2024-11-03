# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS Integration Whatsapp',
    'author': 'Hashmicro',
    'version': '1.1.3',
    'summary': 'POS Integration Whatsapp',
    'depends': ['equip3_general_features', 'equip3_pos_general', 'equip3_pos_membership'],
    'category': 'POS',
    'data': [
        'data/data.xml',
        'data/schedule.xml',
        'views/assets.xml',
        'views/res_config_settings_views.xml',
    ],
    'qweb': [ 
        'static/src/xml/Screens/ReceiptScreen/*.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}