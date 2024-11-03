# -*- coding: utf-8 -*-
{
    'name': "Equip3 Construction Accessright Setting",

    'summary': """
        Manage access right for Construction""",

    'description': """
        This module manages these features :
        1. Users access right
        2. General settings
        3. On/off settings
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Construction',
    'version': '1.1.12',

    # any module necessary for this one to work correctly
    'depends': ['base', 'project',
                'abs_construction_management',
                'equip3_general_setting'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/construction_security.xml',
        'views/res_config_settings_view.xml',
        'views/assets.xml'
    ],
}
