# -*- coding: utf-8 -*-
{
    'name': "Equip3 Rental Report",

    'summary': """
        Equip3 Rental Report""",

    'description': """
        Equip3 Rental Report
    """,

    'author': "Yusup Firmansyah",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Rental',
    'version': '1.1.11',

    # any module necessary for this one to work correctly
    'depends': ['base','browseinfo_rental_management','equip3_rental_operation','ks_dashboard_ninja', 'equip3_rental_other_operation', 'product_expiry'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/ks_rental_data.xml',
        'views/rental.xml',
        'views/menu_icons.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
