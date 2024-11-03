# -*- coding: utf-8 -*-
{
    "name": "Vendor Purchases Order History",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "license": "OPL-1",
    "version": "14.0.2",
    "support": "support@softhealer.com",
    "category": "Purchases",
    "summary": """
Generate Vendor Purchase Order History, Last Purchase Order History Module,
PO Reorder Product Lines, Supplier Request For Quotation History,
Find History From RFQ App, Search Vendor Last Request For Quote Odoo.
""",
    "description": """
This module useful to give vendor purchase history from last purchase orders,
easily reorder product lines from the previous purchase order.
Generate Vendor Purchase Order History Odoo
Give History Of Last purchase Order Module,
Reorder Product Lines From Purchase Order,
Supplier Request For Quotation History, Find History From PO,
Get History Of Last Purchase Order, Search Vendor Last RFQ History Odoo.
Last Purchase Order History Module, PO Reorder Product Lines,
Supplier Request For Quotation History, Find History From RFQ App,
Search Vendor Last Request For Quote Odoo.
""",
    "depends": ["purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_order_history.xml",
        "views/res_config_settings.xml",
        
    ],
    "images": ["static/description/background.png", ],
    "live_test_url": "https://youtu.be/1eJxfDdVUoM",
    "auto_install": False,
    "installable": True,
    "application": True,
    "price": 15,
    "currency": "EUR"
}
