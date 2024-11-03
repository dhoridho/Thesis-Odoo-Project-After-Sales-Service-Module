# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 POS retail report void',
    'author': 'hasnain.datainteger@gmail.com',
    'version': '1.1.1',
    'summary': 'Void report pos Pivot view',
    'depends': ['point_of_sale', 'equip3_pos_order_retail', 'pos_retail'],
    'category': 'Inventory/Inventory',
    'data': [
        'views/pos_order_inherit_view.xml',
        'views/report_pos_order_inherit_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
