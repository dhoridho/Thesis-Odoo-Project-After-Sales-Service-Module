# -*- coding: utf-8 -*-
{
    'name': 'Access Rights Report',
    'version': '1.0.0',
    'summary': """All user access rights in a single view""",
    'description': """All user access rights in a single view""",
    'category': 'Base',
    'author': 'iKreative',
    'version': '1.0',
    'website': "",
    'license': 'AGPL-3',
    'price': 14.0,
    'currency': 'USD',

    'depends': ['base'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/res_users_wizard_view.xml',
        'views/res_users_access_report_view.xml',
        'views/res_users_view.xml',
    ],
    'demo': [],

    'images': ['static/description/banner.png'],
    'qweb': [],

    'installable': True,
    'auto_install': True,
    'application': False,
}
