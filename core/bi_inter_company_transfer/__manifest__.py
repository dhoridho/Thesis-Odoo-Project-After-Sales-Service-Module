# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Auto Inter-Company Transfer-Transection App ",
    "version" : "1.1.6",
    "category" : "Warehouse",
    'summary': 'Auto Inter company Transfer document Auto intercompany transfer document auto intercompany transection automatic inter-company Transection inter company rules setup for multiple company inter company sales inter company purchase inter-company warehouse',
    "description": """
    
            intercompany,
            odoo intercompany,
            odoo intercompany for community,
            intercompany transfer,
            intercompany transaction,
            stock intercompany transaction,
            stock intercompany transfer,
            reverse intercompany transfer,
            reverse intercompany transaction,
    
    """,
    "author": "BrowseInfo",
    "website" : "https://www.browseinfo.in",
    "price": 69,
    "currency": 'EUR',
    "depends" : ['base','sale_management','purchase','stock','account','sale_stock'],
    "data": [
            'security/int_security.xml',
            'security/ir.model.access.csv',
            'data/inter_company_transfer_sequence.xml',
            'views/recompanysettingInherit.xml',
            'views/internal_company_transfer.xml',
            'views/return_inter_company_transfer.xml',
            'views/company_inherit_views.xml',
            'views/res_partner_views.xml'
            ],
    'qweb': [],
    "auto_install": False,
    "installable": True,
    "live_test_url":'https://youtu.be/oZ07noG3YxQ',
    "images":["static/description/Banner.png"],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
