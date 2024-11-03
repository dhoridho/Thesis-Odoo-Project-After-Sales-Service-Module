# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 Kanban View',
    'author': 'Hashmicro / Rajib',
    'version': '1.1.2',
    'summary': 'Customer/Vendor/Product Custom Kanban View',
    'depends': [
        'base_setup', 
        'contacts', 
        'crm', 
        'mail', 
        'membership', 
        'point_of_sale',
        'purchase',
        'sale',
        'stock', 
        'equip3_hashmicro_ui'
    ],
    'category': '',
    'data': [
        'views/assets.xml',
        'views/res_partner_views.xml',
        'views/product_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
