# -*- coding: utf-8 -*-

{
    'name': "Hide Administrator User",
    'version': "1.1.4",
    'summary': """Hide Administrator User""",
    'description': """Restrict the access of the Administrator User to the system. Only the Super Administrator can access the system.""",
    'author': "Hashmicro",
    'website': "https://www.hashmicro.com",
    'category': 'Tools',
    'depends': ['base'],
    'data': [
        'security/security.xml',
        # 'views/assets.xml',
        'views/res_users_views.xml',
        # 'views/log_login_views.xml',
        # 'views/access_rights_profile_views.xml',
    ],
    'license': "AGPL-3",
    'installable': True,
    'application': True,
    'auto_install': False,
}
