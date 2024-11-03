# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Portal Picking",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Warehouse",
    "license": "OPL-1",
    "summary": " View Portal Picking Module, Filter Portal Picking App, Group By Portal Picking, Portal Point Of Sale, See Website Picking, Get Picking Order Details On Portal, Picking Website Odoo",
    "description": """
Currently, in odoo, you can't manage the picking at the portal. Using this module you can see all picking order details from the website portal. You can sort by picking order by newest and name. We have provided a filter option so easy to filter the picking order by last month, last week, last year, this month, this quarter, today, this week & this year. You can easily group by the picking order by none, picking type, status, source document & responsible. Using a search bar you can search picking order details easily. This module helps users to chat, log note, email, message & share attachment inside the picking chatter with each other. Users can schedule activity inside chatter & You can download picking receipt. All changes automatically saved in the backend.""",
    "version": "14.0.1",
    "depends": [
        "stock",
        "portal",
        "utm"
    ],
    "application": True,
    "data": [
        'security/ir.model.access.csv',
        'views/sh_portal_picking_view.xml',
    ],
    "images": ["static/description/background.png", ],
    "live_test_url": "https://youtu.be/w3AUniYOiYQ",
    "auto_install": False,
    "installable": True,
    "price": 100,
    "currency": "EUR"
}
