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
    'name': 'Simplify Group Access',
    'version': '13.0.1.0.1',
    'summary': """ The Access Group feature simplifies access management by allowing you to create rules for specific groups of users based on their assigned roles or job functions. This not only saves time over creating rules for individual users, but it also simplifies the process of managing access permissions for entire departments within the company. It provides a convenient way to efficiently apply access rules, ensuring that users have the appropriate permissions based on their roles and responsibilities. """,
    'sequence': 10,
    'author': 'Terabits Technolab',
    'license': 'OPL-1',
    'website': 'https://www.terabits.xyz',
    'description': """ The Access Group feature simplifies access management by allowing you to create rules for specific groups of users based on their assigned roles or job functions. This not only saves time over creating rules for individual users, but it also simplifies the process of managing access permissions for entire departments within the company. It provides a convenient way to efficiently apply access rules, ensuring that users have the appropriate permissions based on their roles and responsibilities. """,
    'depends': ['simplify_access_management'],
    "price": "99.99",
    "currency": "USD",
    'data': [
        'security/ir.model.access.csv',
        'views/access_groups_view.xml',
        'views/access_management_view.xml',
    ],
    'live_test_url': 'https://www.terabits.xyz/request_demo?source=index&version=16&app=simplify_access_management',
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}