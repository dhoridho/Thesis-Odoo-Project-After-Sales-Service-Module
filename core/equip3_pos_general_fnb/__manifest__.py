# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS General FnB',
    'author': 'HashMicro',
    'version': '1.1.21',
    'summary': 'Equip3 POS General FnB',
    'description': 'Equip3 POS Masterdata FnB',
    'category': 'Point of Sale',
    'depends': [
        'pos_restaurant', 'equip3_pos_masterdata_fnb', 'equip3_pos_general'
    ],
    'data': [ 
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/PosEmployeeMealHistory.xml',
        'views/ReserveOrder.xml',
        'views/SaleOrder.xml',
        'views/PosConfig.xml',
        'report/restaurant_table_qrcode.xml'
    ],
    'qweb': [
        'static/src/xml/ChromeWidgets/*.xml',
        'static/src/xml/PopUps/*.xml',
        'static/src/xml/Screens/Restaurant/FloorScreen/*.xml',
        'static/src/xml/Screens/Restaurant/KitchenScreen/*.xml',
        'static/src/xml/Screens/Restaurant/Receipt/*.xml',
        'static/src/xml/Screens/ProductScreen/Cart/*.xml',
        'static/src/xml/Screens/ProductScreen/ControlButtons/*.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}