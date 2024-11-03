# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Consignment Business Process / Second-hand shops',
    'version' : '1.1.6',
    'price': 148.0,
    'category': 'Warehouse',
    'depends' : [
        'purchase', 
        'stock',
        'sale_management',
        'point_of_sale',
        'website',
        'purchase_stock',
        'equip3_hashmicro_ui',
    ],
    'license': 'Other proprietary',
    'currency': 'EUR',
    'summary': 'This module allow you have process for Consignment business and Second-hand shops.',
    'description': """
Odoo Consignment Process
Consignment
Consignment
Consignment Arrangements
consignment store
Consignment sale
Consignment Booking
consignment agreement
consignment contract
consignment vendor
consignment shops
Consignment stock
consigner
Consigned inventory
Bilty
Consignment Insurance
consignment business
consign
consignors
VMI
vendor managed inventory
thrift shop
customer managed inventory
CMI
https://en.wikipedia.org/wiki/Pawn_shop
pawn shops
sales consignment
retail consignment
consignor
consignee
Second-hand shops
Second-hand shop
Secondhand shops
Second hand
Second hand shop
Benefits of Consignment
consigning
Consignment Arrangement
Consignment Products
Consignments
Consignment Inventory
Consignment Orders
Consignment Purchase Orders
Consignment Sales
Customer Orders
Consignment Agreement Terms
Customers
Consigners
Consignment Reports
PDF Report Vendor Agreement Terms
Consignment Agreement Report
    """,
    'website': 'www.probuse.com',
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'support': 'contact@probuse.com',
    'images': ['static/description/img1.jpg'],
    'live_test_url': 'https://youtu.be/XjwKAybEGO8', #'https://youtu.be/4ezDWNdvhWw',
    
    'data': [
        'views/purchase_order_view.xml',
        'views/sale_order_view.xml',
        'views/product_view.xml',
        'views/pos_order_view.xml',
        'views/my_consignment_template.xml',
        'views/report_consignment_agreement_view.xml',
        'views/stock_picking_view.xml',
        'views/res_partner_views.xml',
        'views/menu.xml',
        'views/cons_menu.xml',
    ],
    'installable': True,
    'application': True,
}
