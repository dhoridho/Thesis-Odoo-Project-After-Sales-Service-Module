# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

{
    'name': 'Product Expiry Alert Dashboard (Community)',
    'summary': 'Product Expiry Alert Dashboard',
    'version': '1.2.2',
    'description': """Product Serial/Lot Expire Dashboard""",
    'author': 'Acespritech Solutions Pvt. Ltd.',
    'category': '',
    'website': "http://www.acespritech.com",
    'price': 49,
    'currency': 'EUR',
    'depends': ['base', 'sale_management', 'stock', 'purchase', 'product_expiry'],
    'data': [
        'security/ir.model.access.csv',
        'data/product_alert_email_template.xml',
        'data/product_expiry_scheduler.xml',
        'views/expiry_assert.xml',
        'views/product_view.xml',
        'views/res_config_setting_view.xml',
        'views/product_expiry_config_view.xml',
        'views/stock_production_lot_view.xml',
        'views/dashboard.xml',
    ],
    'qweb': [
        'static/src/xml/dashboard.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
