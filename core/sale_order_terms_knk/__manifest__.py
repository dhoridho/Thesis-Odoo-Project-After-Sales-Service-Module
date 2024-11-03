# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

{
    'name': "Default Terms & Conditions (Sale)",
    'version': '1.1.1',
    'summary': 'Default Terms & Conditions (Sale) module is used to set Default Terms & Conditions on your Sale Orders and Sale Order report. In this module, the user can write and enable default terms & conditions in settings. After that when the user creates a quotation and Sale order, terms & conditions are automatically shown in the sale order as well as in the Sale order Report.',
    'description': """
This module is used to set Default Terms & Conditions
on your sale Orders and SO report.
=================
    """,
    'license': 'OPL-1',
    'author': "Kanak Infosystems LLP.",
    'website': "https://www.kanakinfosystems.com",
    'category': 'Sales/Sales',
    'depends': ['base', 'sale_management'],
    'images': ['static/description/banner.jpg'],
    'data': [
        'views/sale_view.xml',
    ],
    'sequence': 1,
    'installable': True,
    'application': True,
    'live_test_url': 'https://youtu.be/oaB7ISFQC2w',
}
