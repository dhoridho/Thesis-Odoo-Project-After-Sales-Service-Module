# -*- coding: utf-8 -*-
##############################################################################
# Odoo Additional Function by CTWW
##############################################################################
{
    'name': "Vendor Evaluation",

    'summary': """
        Allows users to evaluate their vendors and store results""",

    'description': """
        This module will be very useful for those who needs to evaluate their vendors, as well as to make better decisions about vendor selection.
        In this module, you will discover some interesting things:
            * 10 evaluation criteria covering many aspects of a vendor
            * Represents the number of points evaluated by priority (from 1 to 5)
            * High flexibility, with unused criteria you can hide it
            * Automatically calculates average score and displays overall rating 
            * Show the most recent overall rating on the Vendor and the RFQ/PO
    """,

    'author': "CTWW",
    'license': 'OPL-1',
    'website': "https://www.linkedin.com/in/ngo-manh-70a68b183/",
    'category': 'Purchases',
    'version': '1.1.2',
    'depends': ['base', 'purchase', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/vendor_evaluation.xml',
        'views/vendor_addition.xml',
    ],
    'demo': [
        # 'data/demo.xml',
    ],
    'currency': 'EUR',
    'price': '14.0',
    'images': ['static/description/vendor_evaluation_01_screenshot.png'],
    'post_init_hook': None,
    'installable': True,
}