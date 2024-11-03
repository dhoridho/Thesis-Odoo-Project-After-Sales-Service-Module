# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 - Inventory Scanning',
    'author': 'Hashmicro / Prince',
    'version': '1.1.3',
    'summary': 'Manage your stock operation activities.',
    'depends': [
        "stock",
    ],
    'category': 'Inventory/Inventory',
    'data': [
        "views/res_config_settings_views.xml",
    ],
    'installable': True,
    'application': True,
}
