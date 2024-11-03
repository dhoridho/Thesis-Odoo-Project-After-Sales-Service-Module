# -*- coding: utf-8 -*-
#################################################################################
# Author      : Terabits Technolab (<www.terabits.xyz>)
# Copyright(c): 2021-23
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can't redistribute/reshare/recreate it for any purpose.
#
#################################################################################

{
    'name': 'Advance Access Management',
    'version': '14.0.1.0.2',
    'summary': """ The "Soft Restrict" feature offers a unique way to access restricted records within associated models, allowing users to read these records even when they may not have directly visible. This feature improve data accessibility and insight, providing a valuable tool for users to work with restricted data in associated models, even when it's not directly visible to them. """,
    'sequence': 10,
    'author': 'Terabits Technolab',
    'license': 'OPL-1',
    'website': 'https://www.terabits.xyz',
    'description': """ The "Soft Restrict" feature offers a unique way to access restricted records within associated models, allowing users to read these records even when they may not have directly visible. This feature improve data accessibility and insight, providing a valuable tool for users to work with restricted data in associated models, even when it's not directly visible to them. """,
    'depends': ['simplify_access_management'],
    'data': [
        'security/ir.model.access.csv',
        # 'views/access_domain_ah.xml',
        'views/access_management_view.xml',
        'views/assets.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
    "price": "147.00",
    "currency": "USD",
    'live_test_url': 'https://www.terabits.xyz/request_demo?source=index&version=14&app=simplify_access_management',
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}