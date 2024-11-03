# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Sale Order Multiple Pricelist",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Sales",
    "summary": "Sale Order Line Multiple Pricelist, SO Multi Line Pricelist,Different Product Sales Order Line Pricelist, Separate Product SO Line Pricelist Module,Non Same Product Quotation Line Pricelist, Multiple Product Sale Order Line Pricelist Odoo",
    "description": """Currently, odoo does not provide any kind of feature for two different products with different price lists in the same order, so you can not set different pricelists in order line in the same order. That's why we made this module. Using this module you can set pricelist for different products into order line. No more effort required just click apply and select price list.
Sale Order Line Multiple Pricelist Odoo, SO Multi Line Pricelist Odoo
 Set Sales Order Line Pricelist For Different Product, Provide SO Line Pricelist For Separate Product Module, Set Quotation Line Pricelist For Non Same Product, Select Sale Order Line Pricelist For Multiple Product Odoo.
  Different Product Sales Order Line Pricelist App, Separate Product SO Line Pricelist Module,Non Same Product Quotation Line Pricelist, Multiple Product Sale Order Line Pricelist Odoo.
""",
    "version": "1.1.2",
    "depends": [
        "sale_management"
    ],
    "application": True,
    "data": [
        "security/ir.model.access.csv",
        'views/sale_order_inherit_view.xml',
        'wizard/sale_order_pricelist_update_wizard.xml',
    ],
    "images": ["static/description/background.png", ],
    "license": "OPL-1",
    "auto_install": False,
    "installable": True,
    "price": 25,
    "currency": "EUR"
}
