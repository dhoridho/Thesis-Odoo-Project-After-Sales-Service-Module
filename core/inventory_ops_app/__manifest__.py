# -*- coding: utf-8 -*-
{
    'name': 'Inventory OPS APP',
    'author': 'Hashmicro/Antsyz- Saravana',
    'version': '1.32',
    'category': 'Stock API',
    'description': '''Stock module will be installed automatically and allow the Ops mobile app to access the Equip System to do the following functionality.
    - Receiving
    - Delivery
    - Internal Transfer
    - Stock Count
    ''',
    'summary': 'Manage your stock operation activities.',
    'depends': ['stock','equip3_inventory_operation', 'equip3_inventory_control', 'sh_all_in_one_mbs'],
    'data': [
        # 'data/stock_count_sequence.xml',
        # 'security/ir.model.access.csv',
        # 'views/stock_count_view.xml',
        # 'views/stock_inventory_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_view.xml',
        'views/stock_move_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
