# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS Flow',
    'author': 'HashMicro',
    'version': '1.1.4',
    'summary': 'Equip3 POS Flow',
    'description': 'Equip3 POS Flow',
    'category': 'Point of Sale',
    'depends': [
        'equip3_pos_general', 
        'equip3_pos_general_fnb',
    ],
    'data': [ 
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/pos_flow_views.xml',
        'data/ir_ui_menu.xml',
    ],
    'qweb': [
        'static/src/xml/pos_flow.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}