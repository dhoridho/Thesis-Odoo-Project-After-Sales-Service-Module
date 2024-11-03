# -*- coding: utf-8 -*-
{
    'name': "equip3_rental_restructure_menu",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Hashmicro",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.3',

    # any module necessary for this one to work correctly
    'depends': ['base','equip3_hashmicro_ui', 'point_of_sale', 'website_sale'],

    # always loaded
    'data': [
        'security/invisible_groups.xml',
        'views/invisible_menus.xml',
        'views/rental_product_view.xml',
    ],

    'installable': True,
    'application': False,
}
