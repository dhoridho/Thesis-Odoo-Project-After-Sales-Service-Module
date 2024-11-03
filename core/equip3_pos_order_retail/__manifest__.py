# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 POS Order Retail',
    'author': 'Hashmicro',
    'version': '1.1.23',
    'summary': 'Manage your stock operation activities.',
    'depends': ['base', 'web', 'pos_retail','equip3_pos_general', 'equip3_POS_master_data_retail'],
    'category': 'POS',
    'data': [
        'security/ir.model.access.csv',
        "views/assets.xml",
        'views/product_cancel_history_views.xml',
        'views/pos_promotion.xml',
        'views/pos_order.xml',
        'views/pos_combo.xml',
        "views/pos_config.xml",
        'views/Restaurant.xml',
        'views/reservation_list.xml',
        'views/hour_group_views.xml'
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
