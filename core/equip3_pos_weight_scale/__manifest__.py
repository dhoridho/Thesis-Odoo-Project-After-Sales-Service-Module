# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS Weight Scale',
    'author': 'HashMicro',
    'version': '1.1.2',
    'summary': 'Equip3 POS Weight Scale',
    'description': 'Equip3 POS Weight Scale',
    'category': 'POS',
    'depends': ['base', 'point_of_sale', 'equip3_pos_general'],
    'data': [
        'views/views.xml',
    ],
    'qweb': [
        'static/src/xml/pos_weight.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}