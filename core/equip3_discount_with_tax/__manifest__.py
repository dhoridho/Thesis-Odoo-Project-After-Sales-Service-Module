# -*- coding: utf-8 -*-
{
    'name': "equip3_discount_with_tax",
    'summary': """""",
    'description': """""",
    'author': "Irfan Suendi",
    'category': 'accounting',
    'version': '1.1.21',
    'depends': ['base', 'account', 'aos_base_account','sale','purchase','branch'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'report/inherit_sale_report.xml',
        'report/inherit_account_report.xml',
        'report/inherit_purchase_report.xml',
    ]
}
