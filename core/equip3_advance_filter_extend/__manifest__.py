# -*- coding: utf-8 -*-
{
    'name': "equip3_advance_filter_extend",

    'summary': """
        Module for add filter additional custom depends from module advance_filter_management """,

    'description': """
        Module for add filter additional custom depends from module advance_filter_management
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    'category': 'Uncategorized',
    'version': '1.1.2',

    'depends': ['advance_filter_management'],

    'data': [
        'views/ir_views.xml',
    ],

    'auto_install': False,
    'installable': True,
    'application': False,
    'post_init_hook': '_settle_filter_pending_approval',
}
