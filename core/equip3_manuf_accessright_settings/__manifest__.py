# -*- coding: utf-8 -*-

{
    'name': 'Equip 3 - Manufacturing Access Right and Settings',
    'version': '1.1.42',
    'category': 'Manufacturing',
    'summary': 'Manufacturing Access Right and Settings',
    'description': '''
    i. Users Setting (Labor | Supervisor/PPIC | Administrator | Manufacturing Accountant)
    ii. Manufacturing Features Installation
    ''',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'mrp',
        'equip3_general_setting'
    ],
    'data': [
        'data/on_upgrade.xml',
        'security/security.xml',
        'views/res_config_settings_views.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
