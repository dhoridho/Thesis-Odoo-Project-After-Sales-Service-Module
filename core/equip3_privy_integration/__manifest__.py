# -*- coding: utf-8 -*-
{
    'name': "equip3_privy_integration",

    'summary': """""",

    'description': """
    """,

    'author': "Hashmicro",
    'website': "http://hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'API',
    'version': '1.1.1',

    # any module necessary for this one to work correctly
    'depends': ['base','base_setup','sh_backmate_theme_adv'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_setting.xml',
        'views/res_partner_views.xml',
        'views/res_company.xml',
        'views/privy_account_registration.xml',
        'views/send_privy_document.xml'

    ],
  
}
