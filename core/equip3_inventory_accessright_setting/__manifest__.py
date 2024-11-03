# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 Inventory Access Right Setting',
    'author': 'Hashmicro / Prince',
    'version': '1.1.21',
    'summary': 'Manage your Inventory Access Right Setting.',
    'depends': ['base', 'stock','purchase', 'product_expiry','equip3_general_setting','dynamic_barcode_labels', 'branch', 'equip3_inventory_base', 'equip3_hashmicro_ui'],
    'category': 'Inventory/Inventory',
    'data': [
        'security/ir.model.access.csv',
        "security/security.xml",
        'views/res_config_settings.xml',
        'views/menu.xml',
        'views/product_views.xml',
        'views/res_users_views.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
