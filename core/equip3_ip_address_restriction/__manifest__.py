# -*- coding: utf-8 -*-

{
    'name': "IP Address Login Validation",
    'version': "1.1.3",
    'summary': """Access Restriction By IP Address & Time""",
    'description': """Access Restriction By IP Address, Time, and Day""",
    'author': "Hashmicro",
    'website': "https://www.hashmicro.com",
    'category': 'Tools',
    'depends': ['base','equip3_general_features'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/assets.xml',
        'views/res_user_views.xml',
        'views/log_login_views.xml',
        'views/access_rights_profile_views.xml',
    ],
    'license': "AGPL-3",
    'installable': True,
    'application': True,
    'auto_install': False,
}
