# -*- coding: utf-8 -*-
{
    'name': "After Sales Dashboard",

    'summary': """
    After Sales Dashboard
    """,

    'author': "Ridho",
    'license': 'OPL-1',
    'currency': 'EUR',
    'category': 'Tools',
    'version': '1.1.1',
    # 'images': ['static/description/ks_sales_banner.jpg'],

    'depends': [
        'ks_dashboard_ninja',
        'after_sales_service'
    ],

    'data': [

        'security/ir.model.access.csv',
        'data/after_sales_dashboard_data.xml',
        # 'data/test_after_sales_dashboard_data.xml',

    ],

}
