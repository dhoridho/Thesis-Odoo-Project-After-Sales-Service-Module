# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2021 Odoo IT now <http://www.odooitnow.com/>
# See LICENSE file for full copyright and licensing details.
#
##############################################################################
{
    'name': 'Sale Product By Location',
    'version': '1.1.2',
    'category': 'Sales',
    'summary': 'Define a specific source location on each Sale Order Line',

    'author': 'Odoo IT now',
    'website': 'http://www.odooitnow.com/',
    'license': 'Other proprietary',

    'description': """
Sale Product By Location
========================
Allows to define a specific source location on each Sale Order line and sell the
products from the different locations, that may not be children of the default
location of the same SO picking type.
    """,

    'depends': ['base', 'sale_management', 'sale_stock'],
    'data': [
            'views/sale_view.xml',
        ],
    'images': ['images/OdooITnow_screenshot.png'],

    'price': 15.0,
    'currency': 'EUR',

    'installable': True,
    'application': True,
    'auto_install': False
}
