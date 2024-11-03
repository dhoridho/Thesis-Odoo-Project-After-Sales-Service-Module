# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Check Delivery Order Status on Web Store",
    "version" : "14.0.0.8",
    "category" : "Website",
    "depends" : ['base','website','portal','stock','sale_management','purchase'],
    "author": "BrowseInfo",
    "summary": 'Website Picking Status on shop delivery order status on shop receipt status on shop website portal picking portal for website delivery portal website receipt portal for delivery order delivery status portal check picking status on portal delivery details',
    "description": """
        Portal Picking for see all picking order details from the website portal.
    """,
    "website" : "https://www.browseinfo.in",
    "price": 89,
    "currency": "EUR",
    "data": [
        'security/ir.model.access.csv',
        'views/picking_portal_template.xml',
    ],
    'qweb': [
    ],
    "auto_install": False,
    "installable": True,
    "live_test_url":'https://youtu.be/-SK6Se9u__I',
    "images":["static/description/Banner.png"],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
