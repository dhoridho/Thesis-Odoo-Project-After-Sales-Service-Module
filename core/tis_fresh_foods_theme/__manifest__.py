# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2021. All rights reserved.

{
    'name': 'Fresh Foods Shop Theme',
    'version': '14.0.0.3',
    'category': 'Theme/Ecommerce',
    'sequence': 1,
    'summary': 'Ecommerce Fresh Foods Shop Theme',
    'description': '''Fresh Foods Shop Theme''',
    'website': 'https://www.technaureus.com/',
    'author': 'Technaureus Info Solutions Pvt. Ltd.',
    'price': 40,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'images': [
        'static/description/banner.png',
        'static/description/theme_screenshot.jpg'],
    'depends': ['website_sale', 'website_sale_wishlist'],
    'live_test_url': 'https://themes.technaureus.com/web/database/selector',
    'data': [
        'security/ir.model.access.csv',
        'views/home_banner_view.xml',
        'views/category_view.xml',
        'views/product_view.xml',
        'views/half_banner_view.xml',
        'views/h_f_fresh_food.xml',
        'views/homepage_fresh_food.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}
