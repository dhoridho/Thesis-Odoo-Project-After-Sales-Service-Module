# -*- coding: utf-8 -*-
{
    'name': "equip3_pos_iot",
    'summary': "",
    'description': "",
    'author': "HashMicro/ Rajib",
    'website': "http://www.hashmicro.com",
    'category': 'POS',
    'version': '1.1.3',
    'depends': [
        'equip3_pos_general', 
        'gravio_connector',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_order_views.xml',
        'views/gravio_log_views.xml',
        'reports/report_pos_order_views.xml',
        'data/ir_cron.xml'
    ],
    'qweb': [
    ],
    'demo': [
    ],
    "images": [
    ],
    
    'installable': True,
    'application': False,
    'auto_install': False
}