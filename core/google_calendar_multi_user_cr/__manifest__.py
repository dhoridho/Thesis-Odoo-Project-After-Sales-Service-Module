# -*- coding: utf-8 -*-
{
    'name': "Google Calendar Multi User",
    'summary': """
        The module adds the possibility to synchronize your google calendar based on user so only respective user can sync and see their google calendar records in Odoo.""",
    'description': """
        Google Calendar Multi User
    """,
    'version': '14.0.0.0',
    'author': "Candidroot Solutions Pvt. Ltd.",
    'website': "https://www.candidroot.com/",
    # any module necessary for this one to work correctly
    'depends': ['google_calendar'],
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/assets.xml'
    ],
    'qweb': [],
    'images': ['static/description/banner.png'],
    'installable': True,
    'live_test_url': '',
    'price': 9.99,
    'currency': 'USD',
    'auto_install': False,
    'application': True,
}
