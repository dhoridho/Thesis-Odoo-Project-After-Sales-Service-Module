# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

{
    'name': "POS Product BOM (Ingredients)",
    'version': '1.1.1',
    'summary': 'This module is used to configure ingredients for pos restaurant foods and manage inventory for such foods(products) in backend | Pos Product Bundal | Product bundal | Inventory for BOM',
    'description': """
This module is used to configure Ingredients for POS Restaurant Foods
and manage inventory for such Foods(Products) in Backend.
=================
    """,
    'license': 'OPL-1',
    'author': "Kanak Infosystems LLP.",
    'website': "https://www.kanakinfosystems.com",
    'category': 'Point of Sale',
    'depends': ['point_of_sale','equip3_pos_masterdata'],
    'data': [
        'views/pos_product_bom.xml',
        'security/ir.model.access.csv'
    ],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': True,
    'price': 60,
    'currency': 'EUR',
    'live_test_url': 'https://youtu.be/xDkKGwMbXKU',
}
