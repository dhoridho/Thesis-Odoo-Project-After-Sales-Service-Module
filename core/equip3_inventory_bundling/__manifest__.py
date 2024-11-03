# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip 3 - Inventory Bundling',
    'author': 'Coderlab Technology',
    'version': '1.1.3',
    'category': 'Inventory',
    'summary': 'Inventory Bundling',
    'depends': [
        'dynamic_product_bundle',        
        'equip3_inventory_operation',
        'product',
    ],
    'data': [
        'views/product_bundle_views.xml',
        # 'views/product_template_views.xml',
    ],
    'installable': True,
}
