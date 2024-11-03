# -*- coding: utf-8 -*-
{
    'name': "Equip3 Sale Purchase",

    'summary': """
        Equip3 Sale Purchase""",

    'description': """
        Equip3 Sale Purchase
    """,

    'author': "Yusup Firmansyah / Hashmicro",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.24',

    # any module necessary for this one to work correctly    
    'depends': ['base','equip3_purchase_operation','equip3_purchase_other_operation','equip3_sale_operation','sh_so_po','bi_inter_company_transfer'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_order_wizard.xml',
        'wizard/purchase_request_line_make_purchase_order.xml',
        'views/purchase_order.xml',
        'views/sale.xml',
        'views/purchase_request.xml',
        'views/stock_picking.xml',
        'views/customer_view.xml',
        'wizard/approval_matrix_customer_reject.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
