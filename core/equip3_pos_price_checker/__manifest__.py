# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS Price Checker',
    'author': 'Hashmicro',
    'version': '1.1.2',
    'summary': 'Equip3 POS Price Checker',
    'description': 'Equip3 POS Price Checker',
    'category': 'Point of Sale',
    'depends': [
        'sh_price_checker_kiosk','equip3_pos_masterdata'
    ],
    'data': [
        'views/assets.xml',
        'views/res_config_setting_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}