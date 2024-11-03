# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 Rental Other Operation',

    'summary': 'Rental Operation Other Management',

    'description': """
        This module manages these features :
        1. Rental Product (Add Fields)
        2. Rental Buffer Time Report (Pivot,Graph,List View)
    """,

    'depends': [
        "browseinfo_rental_management",
        "equip3_rental_masterdata",
        "equip3_rental_operation"
    ],

    'author': "Hashmicro/Muhammad Saleem",
    'category': 'Rental',
    'version': '1.1.7',

    'data': [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/product_views.xml",
        "views/rental_order_line_views.xml",
        "views/rental_buffer_time_views.xml",
    ],
    'installable': True,   
}