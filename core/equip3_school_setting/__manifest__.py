# -*- coding: utf-8 -*-
{
    'name': "School Settings",
    'summary': """
        """,
    'description': """
    """,
    'author': "HashMicro",
    'website': "https://www.hashmicro.com",
    'category': 'School Management',
    'version': '1.1.4',
    'depends': ['base', 'school'],
    'data': [
        'data/school_config_settings_data.xml',
        'security/ir.model.access.csv',
        'views/school_config_settings_views.xml',
    ],
    'auto_install': False,
    'installable': True,
}
