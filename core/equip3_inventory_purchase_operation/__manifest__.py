# -*- coding: utf-8 -*-
{
    'name': "equip3_inventory_purchase_operation",
    'author': "Hashmicro / Wildan",
    'summary': "Manage Between Inventory and Purchase ",
    'website': "http://www.hashmicro.com",
    'category': 'Inventory/Inventory',
    'version': '1.1.8',
    'depends': [
        'base',
        'equip3_inventory_operation',
        'equip3_inventory_control',
        'equip3_purchase_operation',
        ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_rule.xml',
        'wizard/procurement_rfq_wizard.xml',
        'views/purchase_order_view.xml',
        'views/purchase_request_view.xml',
        'views/procurement_planning_model.xml',
    ],
}
