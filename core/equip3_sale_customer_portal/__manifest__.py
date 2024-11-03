# -*- coding: utf-8 -*-

{
    'name': "Equip3 Sale Customer Portal",

    'summary': """
        Manage your customer portal""",

    'description': """
        This module manages these features :
        1. Quotes and Sales Order for Customer Portal
        2. Invoices for Customer Portal
        3. Delivery Order for Customer Portal
    """,

    "author": "Hashmicro",
    'category': 'Sales',
    'version': '1.1.13',

    # any module necessary for this one to work correctly
    "depends": ["website", "sale_stock", "portal", "equip3_sale_accessright_setting", "website_sale"],

    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "views/assets.xml",
        'views/portal_templates.xml',
        'views/my_portal_template.xml',
        'wizard/portal_wizard.xml',
    ],
    "auto_install": False,
    "installable": True,
}
