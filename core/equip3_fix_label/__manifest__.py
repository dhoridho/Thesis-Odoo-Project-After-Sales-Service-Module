# -*- coding: utf-8 -*-
{
    'name': "equip3_fix_label",
    "version": "1.1.1",
    'summary': """
        This module is use to find duplicate label in model ir.model.fields then edit""",

    'description': """
        This module is use to find duplicate label in model ir.model.fields then edit
    """,

    'author': 'HashMicro / Gemilang Wicaksono',
    'website': 'www.hashmicro.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/fix_label_views.xml',
        'views/web_assets.xml',
        'views/clear_cache_views.xml'
    ],
    'qweb' : [
        'static/src/xml/templates.xml'
    ],
}
