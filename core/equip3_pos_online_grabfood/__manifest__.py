# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS Online Outlet GrabFood',
    'author': 'Hashmicro',
    'version': '1.1.2',
    'summary': 'Integrating POS with Online Outlet at GrabFood',
    'depends': ['product','point_of_sale', 'equip3_pos_online_outlet'],
    'category': 'POS',
    'data': [
        'views/assets.xml',
        'views/pos_online_outlet_views.xml',
        'views/product_views.xml',
        'views/pos_online_outlet_campaign_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'qweb': [
        'static/src/xml/PopUps/OnlineOrderReadyTimePopup.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
