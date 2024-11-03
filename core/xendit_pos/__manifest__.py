# -*- coding: utf-8 -*-
{
    'name': "Xendit POS",
    'license': 'LGPL-3',
    'summary': """
        Xendit Odoo POS payment is an official built by Xendit to allow you in accepting online payments instantly. 
        """,

    'description': """
        Xendit Odoo POS payment is an official built by Xendit to allow you in accepting online payments instantly. 
    """,

    'author': "Xendit",
    'website': "https://xendit.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1.1.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'point_of_sale'],

    # always loaded
    'data': [
        'views/pos_payment_method_views.xml',
        # Assets for Odoo 14.0
        'views/point_of_sale_assets.xml'
    ],
    # qweb For Odoo 14.0
    'qweb': [
        'static/src/xml/xendit_qrcode_popup.xml',
    ],
    'images': [
        'static/description/cover.png'
    ],
    'application': True,
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'xendit_pos/static/src/js/PaymentScreen.js',
            'xendit_pos/static/src/js/payment_xendit_pos.js',
            'xendit_pos/static/src/js/models.js',
            'xendit_pos/static/src/js/xendit_qrcode_popup.js'
        ],
        # qweb For Odoo 15.0
        'web.assets_qweb': [
            'xendit_pos/static/src/xml/xendit_qrcode_popup.xml'
        ],
    }
}
