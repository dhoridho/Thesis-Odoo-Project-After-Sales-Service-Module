# -*- coding: utf-8 -*-
{
    'name': 'Purchase Dashboard',
    'version': '1.1.1',
    'summary': """
    User-friendly, detailed and flexible dashboard for purchase module
    | purchase order dashboard 
    | purchase dashboard
    | vendor dashboard
    | supplier dashboard 
    | purchase product dashboard
    | purchase module dashboard
    | PO dashboard
    """,
    'category': 'Purchases',
    'author': 'XFanis',
    'support': 'odoo@xfanis.dev',
    'website': 'https://xfanis.dev',
    'live_test_url': 'https://youtu.be/-wVfMXL0Vls',
    'license': 'OPL-1',
    'price': 15,
    'currency': 'EUR',
    'description':
        """
Detailed Purchase Dashboard
===========================
This module helps to show detailed dashboard based on all purchase orders.
        """,
    'data': [
        'views/assets.xml',
        'views/menu.xml',
    ],
    'depends': ['purchase'],
    'qweb': ['static/src/xml/*.xml'],
    'images': [
        'static/description/xf_purchase_dashboard.png',
        'static/description/dashboard_by_users.png',
        'static/description/dashboard_by_vendors.png',
        'static/description/dashboard_by_products.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
