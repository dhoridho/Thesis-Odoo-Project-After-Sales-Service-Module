# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Purchase Order Digital Signature | Digital Signature Purchase",
    "author": "Softhealer Technologies",
    "license": "OPL-1",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "version": "14.0.1",
    "category": "Purchases",
    "summary": "Digital signature purchase order,Digital sign RFQ, purchase order Digital Signature, request for quotation Digital Signature, RFQ Digital Signature, PO Digital Signature Odoo",
    "description": """This module useful to give digital signature features in purchase order/request for quotation. Digital signature useful for approval, security purpose, contract, etc. If you want to digital sign is compulsory so you can make it just tick 'Check Sign before confirmation' in the configuration setting. After checking this field if you make a purchase order/request for quotation without a sign so it will give you a warning. We have added a new feature for other sign option so you can add details like sign by, designation, sign date-time, etc. You can print a report with a digital signature and other information.""",
    "depends": ['purchase'],
    "data": [
        "views/digital_sign_settings.xml",
        "views/digital_sign.xml",
        "reports/digital_sign_report.xml",
    ],
    "images": ["static/description/background.png", ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "price": "12",
    "currency": "EUR"
}
