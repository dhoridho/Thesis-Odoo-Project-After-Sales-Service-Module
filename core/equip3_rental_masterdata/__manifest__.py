# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 Rental Materdata',

    'summary': 'Rental Operation Management',

    'description': """
        This module manages these features :
        1. Rental Products
    """,

    'depends': [
        "browseinfo_rental_management",
        "general_template",
        'equip3_generate_asset',
        'product', 
        'barcodes', 
        'digest',
        'equip3_hashmicro_ui',
    ],

    'author': "Hashmicro",
    'category': 'Rental',
    'version': '1.1.12',

    'data': [
        "security/ir.model.access.csv",
        "data/ir_cron_check_rental_product_available_for_today.xml",
        "views/rental_order_checklist_item_views.xml",
        "views/rental_product_view.xml",
        "views/rental_menu_views.xml",
        "views/account_asset_asset.xml",
        "views/stock_production_lot_view.xml",
        "views/rental_asset_view.xml"
     ],
    'installable': True,   
}