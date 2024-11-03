# -*- coding: UTF-8 -*-
# Part of Softhealer Technologies.
{
    "name": "All In One Secondary Unit Of Measure | Sale Order Secondary Unit | Purchase Order Secondary Unit | Invoice Secondary Unit | Inventory Secondary Unit",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Extra Tools",
    "license": "OPL-1",
    "summary": """
sales secondary uom app,
purchase secondary unit of measure,
request for quotation multiple uom odoo,
account double uom,
warehouse multiple unit Odoo
""",
    "description": """
Do you have more than one unit of measure in product ?
Yes! so, you are at right palce.
We have created beautiful module to manage secondary unit of product in sales,
purchase,inventory operations and accounting.
It will help you to get easily secondary unit value.
so you don't need to waste your time to calculate that value.
you can also show that value in pdf reports
so your customer/vendor also easily understand that.
""",
    "version": "14.0.3",
    "depends": [
        "sale_management",
        "account",
        "purchase",
        "stock",
    ],
    "application": True,
    "data": [
        "security/secondary_unit_group.xml",
        "views/sh_product_template_custom.xml",
        "views/sh_product_custom.xml",
        "views/sh_sale_order_view.xml",
        "views/sh_purchase_order_view.xml",
        "views/sh_stock_picking_view.xml",
        "views/sh_stock_move_view.xml",
        "views/sh_account_invoice_view.xml",
        "views/sh_stock_scrap_view.xml",
        "report/sh_report_sale_order.xml",
        "report/sh_report_purchase_order.xml",
        "report/sh_report_account_invoice_view.xml",
        "report/sh_report_stock_picking_operation.xml",
        "report/sh_report_deliveryslip.xml",
    ],
    "auto_install": False,
    "installable": True,
    "price": 25,
    "currency": "EUR",
    "images": ['static/description/background.png', ],
    "live_test_url": "https://www.youtube.com/watch?v=KrX_zvlWRdI&feature=youtu.be",
}
