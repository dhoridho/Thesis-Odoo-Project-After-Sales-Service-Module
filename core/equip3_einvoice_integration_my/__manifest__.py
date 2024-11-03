# -*- coding: utf-8 -*-
{
    'name': "equip3_einvoice_integration_my",

    'summary': """""",

    'description': """
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '1.1.6',

    # any module necessary for this one to work correctly
    'depends': ['base','account','l10n_my_ubl_pint'],
    

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'views/assets.xml',
        'data/accounting_setting_my_data.xml',
        'views/notification_wizard.xml',
        'views/res_partner_views.xml',
        'views/account_move.xml',
        # 'views/res_config_settings_views.xml',
        'views/accounting_setting_my.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
