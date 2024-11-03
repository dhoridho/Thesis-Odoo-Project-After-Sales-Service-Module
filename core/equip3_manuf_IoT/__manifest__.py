# -*- coding: utf-8 -*-

{
    'name': 'Equip 3 - Manufacturing IoT',
    'version': '1.1.6',
    'category': 'Manufacturing',
    'summary': '',
    'description': '',
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    'depends': [
        'auth_api_key',
        'equip3_manuf_operations_contd'
    ],
    'data': [
        'data/decimal_precision_data.xml',
        'security/ir.model.access.csv',
        'views/mrp_workcenter_views.xml',
        'views/mrp_gravio_log_views.xml',
        'views/mrp_gravio_record_views.xml',
        'views/menuitems.xml'
    ],
    'demo': [],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False
}
