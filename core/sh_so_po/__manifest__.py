# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name":"Quick Sale Order To Purchase Order",
    "author":"Softhealer Technologies",
    "website":"https://www.softhealer.com",
    "support":"support@softhealer.com",
    "category":"Purchases",
    "license":"OPL-1",
    "summary":"""Quick Sale Order To Purchase Order module, So to PO, Quotation to Request for quotation app, Sales to purchase, sales order to purchase order, quotation to rfq odoo""",
    "description":"""This module is useful to create quickly purchase orders from the sale order. Wasting your important time to make a similar purchase order of your sale order? We will help you to make this procedure quick, just on one click, it will be easy to create a purchase order from quotation or sale order. """,
    "version":"1.1.1",
    "depends": ["sale_management", "purchase"],
    "application":
    True,
    "data": [
        "security/ir.model.access.csv",
        "views/sale_view.xml",
        "views/purchase_view.xml",
        "views/res_config_setting_view.xml",
        "wizard/purchase_order_wizard.xml",
    ],
    "images": [
        "static/description/background.jpg",
    ],
    "live_test_url":"https://youtu.be/m90i8XMVdtU",
    "auto_install":False,
    "installable":True,
    "price":25,
    "currency":"EUR"
}
