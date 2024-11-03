# -*- coding: utf-8 -*-
{
    'name': "Equip3 Asset FMS & Accounting Budget",
    'summary': "Budget Management",
    'author': "HashMicro / Wildan",
    'website': "http://www.hashmicro.com",
    'category': 'FMS',
    'version': '1.1.1',
    'depends': [
        'equip3_asset_fms_operation',
        'equip3_accounting_asset_budget',
        ],
    'data': [
        # 'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/maintenance_work_order_views.xml',
        'views/maintenance_repair_order_views.xml',
    ],
}
