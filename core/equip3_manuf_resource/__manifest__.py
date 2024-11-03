# -*- coding: utf-8 -*-

{
    'name': 'Equip 3 - Manufacturing Resource',
    'version': '1.1.2',
    'category': 'Manufacturing',
    'summary': 'Manufacturing Resource',
    'description': '''
    This module is created to restore the functionality of the resource module in manufacturing 
    which is overridden by the equip3_hr module.
    ''',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'mrp',
        'equip3_hr_working_schedule'
    ],
    'data': [
        'data/resource_data.xml',
        'views/resource_views.xml',
        'views/mrp_workcenter_views.xml'
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False
}
