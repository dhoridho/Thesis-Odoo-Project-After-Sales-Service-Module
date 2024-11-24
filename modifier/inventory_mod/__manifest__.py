# -*- coding: utf-8 -*-
{
    'name': "Inventory Modifier",

    'summary': """
        Inventory Modifier""",

    'description': """
        
    """,

    'author': "Ridho",
    'website': "http://www.hashmicro.com",

    # Categories can be used to     filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Modifier',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'product',
                'stock',
                ],

    # always loaded
    'data': [
        'views/product.xml',
        'security/ir.model.access.csv',
        'report/paperformat.xml',
        'report/report.xml',
        'report/lot_barcode_label.xml',
        'views/stock_move_operation_views.xml',
        'data/server_action2.xml',
        'data/server_action_product.xml',
        'views/attachment_lot.xml',
        'views/stock.xml',
        # 'views/res_partner.xml',
        # 'views/product_supplierinfo.xml',
    ],

}
