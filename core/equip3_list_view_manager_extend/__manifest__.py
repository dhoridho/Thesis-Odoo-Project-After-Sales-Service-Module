# -*- coding: utf-8 -*-
{
    'name': "equip3_list_view_manager_extend",

    'summary': """
        Module extend from ks_list_view_manager """,

    'description': """
        Module extend from ks_list_view_manager 
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    'category': 'Uncategorized',
    'version': '0.0.4',

    'depends': ['ks_list_view_manager','equip3_hashmicro_ui'],

    'data': [
        'views/assets_views.xml',
        'views/res_views.xml',
        'views/user_specific_views.xml',
    ],

    'auto_install': False,
    'installable': True,
    'application': False,
}
