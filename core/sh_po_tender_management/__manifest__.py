# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Purchase Tender Management",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "license": "OPL-1",
    "category": "Purchases",
    "summary": " Manage Multiple Tenders, Multiple Tender  Single List Module, Multiple Tenders Request For Quotation Manage, Same Partner Tender Management App, Purchase Tender Management, PO Tender Management Odoo.",
    "description": """
    Nowadays in a competitive market, several vendors sell the same products and everyone has their price so it will difficult to manage multiple tenders at a time even in odoo there is no kind of feature where you can manage multiple tenders in a single list. Our this module will provide a platform where you can manage multiple tenders RFQs. Using this module you can easily confirm, cancel tender RFQs in one list. This module provides many stages for manage tender like Draft, Confirm, Bid Selection, Close, Cancel, etc. Using this module you can make a purchase order of multiple RFQs in a single click If you have more than one tender RFQ from the same partner so it will merge in one purchase order. You can easily send a tender pdf report to your partner's email.""",
    "version": "1.1.1",
    "depends": [
        "purchase",
        "stock",
        "account",
        "mail",
        "portal",
        "utm"
    ],
    "application": True,
    "data": [
        'security/sh_purchase_tender_security.xml',
        'security/ir.model.access.csv',
        'data/sh_purchase_agreement_data.xml',
        'views/res_config_seetings.xml',
        'views/sh_purchase_agreement_type_view.xml',
        'views/res_users.xml',
        'views/sh_purchase_agreement_view.xml',
        'views/sh_bidline_view.xml',
        'views/sh_report_purchase_tender_template.xml',
        'views/report_analyze_quotations.xml',
        'views/report_views.xml',
        'data/sh_purchase_tender_email_data.xml',
        'wizard/sh_update_qty_wizard_view.xml',
        'wizard/sh_purchase_order_wizard_view.xml',
    ],
    "images": ["static/description/background.png", ],
    "live_test_url": "https://youtu.be/U11c99oX-m0",
    "auto_install": False,
    "installable": True,
    "price": 60,
    "currency": "EUR"
}
