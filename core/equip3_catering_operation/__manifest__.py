# -*- coding: utf-8 -*-
{
    'name': "equip3_catering_operation",

    'summary': """
        Manage Catering Operation""",

    'description': """
        - Catering Order
        - Catering Order to Delivery Order
        - Scheduler creating delivery order
    """,

    'author': "HashMicro",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.20',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'mail',
        'equip3_catering_masterdata',
        'equip3_sale_masterdata',
        'equip3_hashmicro_ui',
        'equip3_general_setting'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/rule.xml',
        'data/sequence.xml',
        'data/ir_cron.xml',
        'static/src/xml/assets.xml',
        'wizard/change_menu_wizard.xml',
        'views/catering_operation_templates.xml',
        'views/menu_category.xml',
        'views/menu_planner.xml',
        'views/views.xml',
        'views/menu_icons.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}