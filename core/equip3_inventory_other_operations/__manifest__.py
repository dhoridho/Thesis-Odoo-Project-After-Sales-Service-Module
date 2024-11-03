# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 Inventory Other Operations',
    'author': 'Hashmicro/Kalkivi Khunt',
    'website': 'www.hashmicro.com',
    'version': '1.1.12',
    'summary': 'Inventory Other Operations',
    'depends': [
        'equip3_inventory_operation', 'equip3_hashmicro_ui',
    ],
    'category': 'Inventory/Inventory',
    'data': [
        'security/ir.model.access.csv',
        'views/assets_view.xml',
        'views/repair_order_view.xml',
        'views/internal_order.xml',
        'views/report_repair_cost_details.xml',
        'views/repair_menu.xml',
        'views/menu_views.xml',
        'wizards/picking_wizard_import.xml',

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
