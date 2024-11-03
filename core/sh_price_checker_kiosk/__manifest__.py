# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
{
    'name': 'Product Price Checker',

    'author': 'Softhealer Technologies',

    'website': 'https://www.softhealer.com',

    'support': 'support@softhealer.com',

    'version': '14.0.4',
    
    "license": "OPL-1",

    'category': 'Extra Tools',

    'summary': "Product Price Checker,Product Kiosk,Product Information, Product Price By Barcode Number,Find Product Using Barcode No, Product Detail By Barcode, Scan Barcode For Price Module,Check Product Price, Product Price Odoo",
    'description': """Do you want to check the product price with product details quickly? This module allows you to check the product price using barcode no. User can enter barcode number by touch keyboard and it will be auto-scan through barcode scanner hardware attached, After a successful scan, You can see product information like product image, product code, product barcode, product sales price, available stock, product specification, product category. It can be useful for the customer also as a customer can easily check product information from the touchscreen or normal screen. we have a virtual keyboard so the user can use in touchscreen. everything is given configurable so the user can easily enable/disable as per his requirement from configuration screen, cheers!""",

    'depends': [
        'product',
        'barcodes',
        'portal'
    ],

    'data': [
        'security/price_checker_security.xml',
        'views/res_config_setting_view.xml',
        'views/web_asset_backend_template.xml',
        'views/checker_kiosk_view.xml',
        'views/res_users.xml',
    ],
    'qweb': [
        "static/src/xml/checker_kiosk.xml",
    ],
    "images": ["static/description/background.png", ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 100,
    "currency": "EUR"
}
