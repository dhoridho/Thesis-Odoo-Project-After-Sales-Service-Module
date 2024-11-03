# -*- coding: utf-8 -*-
{
    'name': "equip3_inventory_approval_masterdata",

    'summary': """
        Manages the approval matrix for Inventory-related master data""",

    'description': """
        Manages the approval matrix for Inventory-related master data
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.1',

    # any module necessary for this one to work correctly
    'depends': ['base','equip3_inventory_masterdata'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/stock_inventory_approval_matrix.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
