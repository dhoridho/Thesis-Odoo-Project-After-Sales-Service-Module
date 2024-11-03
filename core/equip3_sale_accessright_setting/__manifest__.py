# -*- coding: utf-8 -*-
{
    'name': "Equip3 Sale Access Right Setting",
    'summary': """
        Manage access right for sales""",
    'description': """
        This module manages these features :
        1. Users access right
        2. General settings for sales
        3. On/off settings
    """,
    'author': "Hashmicro",
    'category': 'Sales',
    'version': '1.3.7',

    # any module necessary for this one to work correctly
    'depends': [
        'sale_stock',
        'account',
        'sh_sale_credit_limit',
        'sh_sale_reports',
        'crm',
        'quotation_expiry_reminder',
        'equip3_general_setting',
        'sh_all_in_one_mbs'
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/equip3_sale_security.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/res_config_settings_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}