# -*- coding: utf-8 -*-
# Copyright 2023 IZI PT Solusi Usaha Mudah
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
# noinspection PyUnresolvedReferences,SpellCheckingInspection
{
    "name": """Tiktok Shop Connector""",
    "summary": """Integrating Odoo with Marketplace: Tiktok""",
    "category": "Sales",
    "version": "1.1.6",
    "development_status": "Alpha",  # Options: Alpha|Beta|Production/Stable|Mature
    "auto_install": False,
    "installable": True,
    "application": True,
    "sequence": -99,
    "author": "IZI PT Solusi Usaha Mudah",
    "support": "admin@iziapp.id",
    "website": "https://www.iziapp.id",
    "license": "OPL-1",
    "images": [
        'static/description/banner.gif'
    ],
    "price": 1140,
    "currency": "USD",

    # any module necessary for this one to work correctly
    'depends': ['base', 'izi_marketplace'],

    # always loaded
    'data': [
        # data
        'data/data_tiktok_state_order.xml',
        'data/mp_partner.xml',
        # 'data/product.xml',

        'wizard/wiz_tiktok_order_reject.xml',
        'views/action/action_menu.xml',
        'views/mp_account.xml',
        'views/menu.xml',
        'views/mp_tiktok_shop.xml',
        'views/mp_tiktok_logistic.xml',
        'views/sale_order.xml',
        'views/stock_picking.xml',
        'views/mp_product.xml',
        'views/product_template.xml',
        'views/mp_stock.xml',
        'views/mp_tiktok_category.xml',

        # 'views/wizard/views.xml',

        'security/ir.model.access.csv',
        'security2/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
