# -*- coding: utf-8 -*-
{
    'name': "Batch Picking Modifier",

    'summary': """
        Batch Picking Modifier""",

    'description': """
        -Domain picking line in Batch picking
        - add field nomor container
        - add partner in line transfer
        - add dpl quantity in operatrion
    """,

    'author': "Ridho",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Modifier',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'inventory_mod',
               ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/wizard_dpl_quantity.xml',
        # 'views/views.xml',
        # 'views/move.xml',
        'views/lot.xml',
        # 'views/landed_cost.xml',
        # 'views/stock_batch_picking_templates_inherit.xml',
        'views/quant.xml',
        # 'wizard/stock_lot_serializer.xml'
    ],

}
