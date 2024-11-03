# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Purchase Shipment And Bill Status",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Purchases",
    "summary": "purchase order shipment Status module, filter purchase order shipment, po partial delivery app, find full shipment in po, status of full delivery odoo",
    "description": """
This module is useful to get the status of shipment and bill of purchase orders. Easily filters purchase orders with fully shipped, partial shipped, paid, partially paid.
purchase order shipment module, filter purchase order shipment, po partial delivery app, find full shipment in po, status of full delivery odoo
                    """,
    "version": "1.1.1",
    "depends": [
        "purchase",
        "stock",
    ],
    "application": True,
    "data": [
        'views/purchase_view.xml',
    ],
    "images": ["static/description/background.png", ],
    "live_test_url": "https://youtu.be/vt5961j1DBg",
    "license": "OPL-1",
    "auto_install": False,
    "installable": True,
    "price": 15,
    "currency": "EUR"
}
