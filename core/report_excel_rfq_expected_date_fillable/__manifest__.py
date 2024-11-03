# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2020 GRIMMETTE,LLC <info@grimmette.com>

{
    'name': 'Request for Quotation with Expected Date (Fillable) (XLSX)',
    'version': '1.0.0',
    'category': 'Extra Tools',
    'summary': 'Request for Quotation with Expected Date (Fillable) (XLSX)',     
    'price': 0.00,
    'currency': 'EUR',
    "license": "OPL-1",     
    'description': """
Request for Quotation with Expected Date (Fillable) (XLSX)
====================================
Request for Quotation with Expected Date (Fillable) in MS Excel format (XLSX)
Generate the Excel Report from a Template.
Report for Report Designer (XLSX, XLSM). 
    Odoo Report XLSX  Create Excel Report Excel Reports Accounting Reports Financial Report Financial Reports Stock Reports Inventory Reports \
    Dynamic Sale Analysis Reports Export Excel Export xlsx Project Reports Warehouse Reports Purchases Reports Marketing Reports Sales Reports \
    Report Designer Reports Designer Report Builder Reports Builder Product Report Customer Report POS Reports POS Report Analysis Report \
    BI Report BI Reports BI Business Intelligence Report Business Intelligence Reports BI Analytics BI Analytic Data Analysis Reporting Tool
    """,
    'author': 'GRIMMETTE',
    'support': 'info@grimmette.com',
#     'live_test_url': "http://68.183.4.193:8069",
    'depends': ['account', 'purchase', 'product'],
    'images': ['static/description/banner_rep.png'],
    'data': [
        'data/request_for_quotation_expected_date_fillable_xlsx.xml',
    ],
    'qweb': [
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    "pre_init_hook": "pre_init_check",
}



