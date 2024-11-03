# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Purchase Order Revision",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "license": "OPL-1",
    "category": "Purchases",
    "summary": "Purchases Order Revision, PO Revision,RFQ Revision,Request For Quotation Revisions,Purchase Quote Revision,Revision History,Revise Purchase Order, Revision Request For Quotation,Revision Order Of Purchase,Generate Revision Order Odoo",
    "description": """This module allows to create revision of the cancelled purchase order/request for quotation with the same base number. You can maintain a log of generated revisions. Which can be useful to keep track of all purchase order history.""",
    "version": "1.1.2",
    "depends": [
        "purchase",
    ],
    "application": True,
    "data": [
        "views/purchase_config_settings.xml",
        "views/purchase_order.xml",
    ],
    "images": ["static/description/background.png", ],
    "auto_install": False,
    "installable": True,
    "price": 20,
    "currency": "EUR"
}
