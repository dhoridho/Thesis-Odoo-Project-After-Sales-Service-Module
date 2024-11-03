# -*- coding: utf-8 -*-
{
    'name': "equip3_accounting_salepurchase_operation",
    'summary': """Sale Purchase Operation""",
    'description': """ """,
    'author': "Hashmicro / Prince",
    'website': "",
    'category': 'accounting',
    'version': '1.3.29',
    'depends': [
        'branch',
        'sale',
        'purchase_request',
        'stock',
        'equip3_purchase_operation',
        'equip3_sale_operation'
        # 'equip3_accounting_operation_extd',
    ],
    'data': [
        "security/ir.model.access.csv",
        'views/account_move_views.xml',
        'views/purchase_request_views.xml',
        'views/stock_picking_views.xml',
        'wizard/order_picking_views.xml',
        'wizard/product_cost_adjustment_views.xml',
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True
}
