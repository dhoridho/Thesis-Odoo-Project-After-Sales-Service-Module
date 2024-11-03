# -*- coding: utf-8 -*-
{
    'name': "Equip3 Sale Forecast",

    'summary': """
        Manage your Sales Forecast""",

    'description': """
        This module manages these features :
        1. Multicompany in Sale Forecast Module
    """,

    'author': "Hashmicro",
    'category': 'Sale',
    'version': '1.1.4',

    # any module necessary for this one to work correctly
    'depends': [
        'ks_sales_forecast',
    ],

    # always loaded
    'data': [
        'views/loyalty_view.xml',
        'security/rule.xml',
    ],
    # only loaded in demonstration mode
    'demo': [

    ],
}