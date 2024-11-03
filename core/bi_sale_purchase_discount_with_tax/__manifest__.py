# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Odoo Global Discount on Sale,Purchase & Invoice with Tax calculation',
    'version': '1.1.10',
    'category': 'Sales',
    'sequence': 14,
    'price': 55,
    'currency': "EUR",
    'summary': 'Sale discount with tax sales discount invoice discount purchase discount purchase order discount fixed discount on sale invoice discount vendor discount on purchase vendor bill discount All in one Discount after tax amount global discount before tax amount',
    'description': """
Manage sales and purchase orders and Invoice Discount Manages the Discount in Sale order , Purchase Order and in whole Sale order/Purchase order basis on Fix
and Percentage wise as well as calculate tax before discount and after

discount and same for the Invoice.
discount on sale purchase invoice with tax
discount with tax on Sale Purchase Invoice Discount
Sale Purchase Invoice Discount
tax calculation with discount 
sale discount
purchase discount
Invoice Discount
discount with tax
tax without discount
Discount on Sale Order
Discount On Purchase Order
discount on purchase orderline
Discount on Sale Orderline
Discount on Invoice Line (Invoices & Bills)
Account Discount
customer discount
This module also have following separated features.
    -Global Discount on Invoice, Discount on purchase order, Global Discount on Sales order
    -Discount on sale order line, Discount on purchase order line, Discount on Invoice line
    -Discount purchase, Discount sale,Discount Invoice, Discount POS, Disount Order,Order Discount, Point of Sale Discount,Discont on pricelist, Fixed Discount, Percentage Discount, Commission, Discount Tax.
    -All in One Discount, All discount, Sales Discount, Purchase Discount,Sales Invoice Discount, Purchase Invoice Discount,Odoo Discount, OpenERP Discount, Sale Order Discount, Purchase order discount, Invoice line Discount,Discount with Taxes, Order line Discount, sale line discount, purchase line discount,Discount on line.Discount Feature, Discount for all

odoo Global Discount on Invoice Discount on purchase order Global Discount on Sales order odoo
odoo Discount on sale order line Discount on purchase order line Discount on Invoice line
odoo Discount purchase Discount sale Discount Invoice Discount POS Disount Order Order Discount odoo
odoo discount Point of Sale Discount odoo Discont on pricelist Fixed Discount Percentage Discount Commission 
odoo Discount Tax odoo sales Global discount purchase Global discount invoice Global discount
odoo All in One Discount All discount Sales Discount Purchase Discount Sales Invoice Discount Purchase Invoice Discount
Odoo Discount OpenERP Discount Sale Order Discount Purchase order discount Invoice line Discount odoo
odoo Discount with Taxes Order line Discount sale line discount purchase line discount Discount on line discount
odoo Discount Feature Discount for all discount and same for the Invoice.
odoo discount on sale purchase invoice with tax discount with tax on Sale Purchase Invoice Discount
odoo Sale Purchase Invoice Discount tax calculation with discount 
odoo sale discount purchase discount
odoo Invoice Discount odoo discount with tax
odoo tax without discount odoo Discount on Sale Order Discount On Purchase Order discount on purchase orderline
odoo Discount on Sale Orderline Discount on Invoice Line odoo discount on Invoices discount vendor Bills
odoo vendor bills discount on vendor bills odoo vendor bill discount on vendor bill odoo
Account Discount customer discount
odoo discount with taxes sales discount with taxes purchase discount with taxes 
odoo sale discount after taxes purchase discount after taxes discount odoo
odoo sale discount before taxes purchase discount before taxes discount odoo
This module also have following separated features.
    -Global Discount on Invoice, Discount on purchase order, Global Discount on Sales order
    -Discount on sale order line, Discount on purchase order line, Discount on Invoice line
    -Discount purchase, Discount sale,Discount Invoice, Discount POS, Disount Order,Order Discount, Point of Sale Discount,Discont on pricelist, Fixed Discount, Percentage Discount, Commission, Discount Tax.
    -All in One Discount, All discount, Sales Discount, Purchase Discount,Sales Invoice Discount, Purchase Invoice Discount,Odoo Discount, OpenERP Discount, Sale Order Discount, Purchase order discount, Invoice line Discount,Discount with Taxes, Order line Discount, sale line discount, purchase line discount,Discount on line.Discount Feature, Discount for all

Manages the Discount in Sale order , Purchase Order and in whole Sale order/Purchase order basis on Fix
and Percentage wise as well as calculate tax before discount and after
discount and same for the Invoice.
This module also have following separated features.
    -Global Discount on Invoice, Discount on purchase order, Global Discount on Sales order
    -Discount on sale order line, Discount on purchase order line, Discount on Invoice line
    -Discount purchase, Discount sale,Discount Invoice, Discount POS, Disount Order,Order Discount, Point of Sale Discount,Discont on pricelist, Fixed Discount, Percentage Discount, Commission, Discount Tax.
    -All in One Discount, All discount, Sales Discount, Purchase Discount,Sales Invoice Discount, Purchase Invoice Discount,Odoo Discount, OpenERP Discount, Sale Order Discount, Purchase order discount, Invoice line Discount,Discount with Taxes, Order line Discount, sale line discount, purchase line discount,Discount on line.Discount Feature, Discount for all

discount and same for the Invoice.
discount on sale purchase invoice with tax
discount with tax on Sale Purchase Invoice Discount
Sale Purchase Invoice Discount
tax calculation with discount 
sale discount
purchase discount
Invoice Discount
discount with tax
tax without discount
Discount on Sale Order
Discount On Purchase Order
discount on purchase orderline
Discount on Sale Orderline
Discount on Invoice Line (Invoices & Bills)
Account Discount
customer discount

odoo sale invoice discount invoice sale discount odoo vendor bill discount purchase vendor bill discount
odoo Global Discount on Invoice Discount on purchase order Global Discount on Sales order odoo
odoo Discount on sale order line Discount on purchase order line Discount on Invoice line
odoo Discount purchase Discount sale Discount Invoice Discount POS Disount Order Order Discount odoo
odoo discount Point of Sale Discount odoo Discont on pricelist Fixed Discount Percentage Discount Commission 
odoo Discount Tax odoo sales Global discount purchase Global discount invoice Global discount
odoo All in One Discount All discount Sales Discount Purchase Discount Sales Invoice Discount Purchase Invoice Discount
Odoo Discount OpenERP Discount Sale Order Discount Purchase order discount Invoice line Discount odoo
odoo Discount with Taxes Order line Discount sale line discount purchase line discount Discount on line discount
odoo Discount Feature Discount for all discount and same for the Invoice.
odoo discount on sale purchase invoice with tax discount with tax on Sale Purchase Invoice Discount
odoo Sale Purchase Invoice Discount tax calculation with discount 
odoo sale discount purchase discount
odoo Invoice Discount odoo discount with tax
odoo tax without discount odoo Discount on Sale Order Discount On Purchase Order discount on purchase orderline
odoo Discount on Sale Orderline Discount on Invoice Line odoo discount on Invoices discount vendor Bills
odoo vendor bills discount on vendor bills odoo vendor bill discount on vendor bill odoo
Account Discount customer discount
odoo sale discount after taxes purchase discount after taxes discount odoo
odoo sale discount before taxes purchase discount before taxes discount odoo
=========================================
Manages the Discount in Sale order and Purchase order line basis on Fix
and Percentage wise as well as for the Invoice.
""",

    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.in',
    'depends': ['base','sale','sale_management','account','purchase','stock'],
    'data': [
        'views/sale_view.xml',
        'views/purchase_view.xml',
        'report/inherit_sale_report.xml',
        'report/inherit_account_report.xml',
        'report/inherit_purchase_report.xml',
        
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'live_test_url': "https://youtu.be/BrxectuViQg",
    'images':['static/description/Banner.png'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
