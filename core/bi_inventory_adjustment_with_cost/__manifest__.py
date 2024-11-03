# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Inventory Adjustment with Cost Price Odoo",
    "version" : "14.0.0.4",
    "category" : "Warehouse",
    'summary': 'Inventory Adjustment Cost Price Inventory Adjustment costing Inventory Adjustment with valuation costing manual costing on Inventory Adjustment with costing Inventory valuation cost with inventory cost price for valuation costing with Inventory Adjustment',
    "description": """
    
    Inventory Adjustment with Cost 

    Inventory adjustment with cost in odoo,
    set up cost price in inventory adjustment,
    generate journal entry from stock move in odoo,
    configured inventory adjustment with cost in odoo,
    
    """,
    "author": "BrowseInfo",
    "website" : "https://www.browseinfo.in",
    "price": 29,
    "currency": 'EUR',
    "depends" : ['base','account','stock','stock_account'],
    "data": [
        'views/setting.xml',
        'views/inventory.xml',
    ],
    'qweb': [
    ],
    "auto_install": False,
    "installable": True,
    "live_test_url":'https://youtu.be/nBEl6rW8utY',
    "images":["static/description/Banner.png"],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
