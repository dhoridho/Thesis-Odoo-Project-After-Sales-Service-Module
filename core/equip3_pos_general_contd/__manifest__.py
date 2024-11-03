# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS General Contd',
    'author': 'Hashmicro',
    'version': '1.1.14',
    'summary': 'Equip3 POS General Contd',
    'depends': [ 'equip3_pos_general'],
    'category': 'POS',
    'data': [
        'views/assets.xml',
        'views/pos_config_views.xml',
        'views/pos_session_views.xml',
    ],
    'qweb':[ 
        'static/src/xml/PopUps/*.xml',
        'static/src/xml/Screens/PosOrder/PosOrderDetail.xml', 
        'static/src/xml/Screens/PosOrder/PosOrderLines.xml', 
        'static/src/xml/Screens/ProductScreen/ProductScreen.xml', 
        'static/src/xml/Screens/OrderHistoryLocal/*.xml', 
        'static/src/xml/Screens/ProductScreen/*.xml', 
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}