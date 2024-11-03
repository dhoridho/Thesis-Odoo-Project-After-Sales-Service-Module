# -*- coding: utf-8 -*-
{
    'name': "equip3_catering_masterdata",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.16',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'mail',
        'product',
        'stock',
        'equip3_sale_operation'
    ],

    # always loaded
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/catering_view.xml',
        'views/catering_menu_planner.xml',
        'views/res_config_settings_views.xml',
        'views/templates.xml',
        'views/menu_icons.xml',
        'report/catering_menu_planner_report.xml',
        'report/report.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}