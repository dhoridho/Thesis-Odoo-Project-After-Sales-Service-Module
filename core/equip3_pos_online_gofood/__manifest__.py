# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS Online Outlet GoFood/Gobiz',
    'author': 'Hashmicro',
    'version': '1.1.1',
    'summary': 'Integrating POS with Online Outlet at Gobiz',
    'depends': ['product','point_of_sale', 'equip3_pos_online_outlet'],
    'category': 'POS',
    'data': [
        'views/assets.xml',
        'data/ir_cron_data.xml',
        'security/ir.model.access.csv',
        'views/pos_online_outlet_gobiz_subscription_views.xml',
        'views/pos_online_outlet_views.xml',
        'views/pos_online_outlet_campaign_views.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'qweb': [  
    
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
