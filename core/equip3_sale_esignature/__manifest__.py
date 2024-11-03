# -*- coding: utf-8 -*-
{
    'name': "Equip3 Sale E-Signature",

    'summary': """
        Manage digital signature integrate with Privy""",

    'description': """
        This module manages these features :
        1. E-Signature in settings
        2. Sales Orders Quotations
        3. Sales Orders Customers
    """,

    'author': "Hashmicro",
    'category': 'Sales',
    'version': '1.1.8',

    # any module necessary for this one to work correctly
    'depends': [
        'sale',
        'website',
        'portal',
        "equip3_sale_masterdata",
    ],

    # always loaded
    'data': [
        'security/rule.xml',
        'security/ir.model.access.csv',
        'views/customer_signature_templates.xml',
        # 'data/customer_signature_menu.xml',
        'views/res_config_setting_view.xml',
        'views/sale_view.xml',
        'views/partner_view.xml',
        'views/sale_customer_signature.xml',
        'views/customer_country_template.xml',
        "views/portal_template_views.xml",
        'views/asset_views.xml',
    ],
    'auto_install': False,
    'installable': True,

    'demo': [

    ],
}