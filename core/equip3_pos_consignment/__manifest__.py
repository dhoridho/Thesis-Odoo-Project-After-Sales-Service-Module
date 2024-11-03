# -*- coding: utf-8 -*-
{
    'name': 'Equip3 Consignment Module',
    'summary': 'Hashmicro Consignment Module For POS',
    'description': 'Consignment module for POS',
    'author': 'HashMicro',
    'website': 'https://hashmicro.com',
    'category': 'POS',
    'version': '1.1.12',
    'depends': [
        'base',
        'purchase',
        'sale',
        'point_of_sale',
        'dev_purchase_down_payment',
        'equip3_purchase_operation',
        'equip3_inventory_consignment',
        'equip3_sale_operation',
    ],

    'data': [
        'views/purchase_order.xml',
        'views/purchase_request.xml',
        # 'report/marginal_report.xml',
        'views/consignment_agreement_views.xml',
        'views/pos_order_views.xml',
    ],
}
