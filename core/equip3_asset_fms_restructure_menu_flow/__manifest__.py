# -*- coding: utf-8 -*-
{
    'name': "Equip3 FMS Restructure Menu Flow",
    'summary': "Equip3 FMS Restructure Menu Flow",
    'author': "",
    'version': '1.1.1',
    'category': 'Uncategorized',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/asset_flow.xml',
    ],
    'qweb': [
        'static/xml/asset_flow.xml',
    ],
    'installable': True,
    'application': False,
}
