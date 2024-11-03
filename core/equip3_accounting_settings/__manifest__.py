# -*- coding: utf-8 -*-
{
    'name': "equip3_accounting_settings",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.4',

    # any module necessary for this one to work correctly
    'depends': ['base','account', 'equip3_general_features'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/accounting_setting_data.xml',
        'views/accounting_setting.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    "application": True,
    "auto_install": True,
    "installable": True,
}
