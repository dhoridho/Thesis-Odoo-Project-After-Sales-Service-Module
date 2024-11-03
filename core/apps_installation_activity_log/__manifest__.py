# -*- coding: utf-8 -*-
{
    'name': "Apps Installation Activity Log",
    'summary': 'Apps Installation Activity Log',
    'description': """
                Apps Installation Activity Log
    """,
    'author': 'HashMicro / Prince',
    'website': 'www.hashmicro.com',
    'category': '',
    'version': '1.1.1',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/apps_installation_activity_log_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
