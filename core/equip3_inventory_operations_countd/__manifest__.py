# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 Operations Countd',
    'author': 'Hashmicro / Prince',
    'version': '1.1.15',
    'summary': 'Manage your Inventory tracking.',
    'depends': ['stock_picking_batch', 'branch', 'general_template', 'equip3_inventory_operation'],
    'category': 'Inventory/Inventory',
    'data': [
        "data/ir_sequence.xml",
        'security/ir.model.access.csv',
        'views/batch_transfer_view.xml',
        'views/menu_views.xml',
        'wizard/stock_picking_batch_validate_wizard.xml',
        'report/stock_picking_batch.xml',
        'security/ir_rule.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
