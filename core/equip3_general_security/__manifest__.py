# -*- coding: utf-8 -*-
{
    'name': "equip3_general_security",

    'summary': """""",

    'description': """""",

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'general',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','website','web','http_routing','auth_signup'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/crash_manager.xml',
        'views/templates.xml',
        'views/views.xml',
        'views/res_user.xml',
    ],
    

        'qweb': [
        'static/src/xml/crash_manager.xml',
    ],
    'post_load': '_patch_http'
        
}
