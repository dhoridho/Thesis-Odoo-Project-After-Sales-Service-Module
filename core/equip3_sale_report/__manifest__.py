# -*- coding: utf-8 -*-
{
    'name': "Equip3 Sale Report",

    'summary': """
        Manage your sale reports""",

    'description': """
        This module manages these features :
        1. Sales Analysis
        2. Customer Report
        3. Product Report
    """,

    'author': "Hashmicro",
    'category': 'Sales',
    'version': '1.1.33',

    # any module necessary for this one to work correctly
    'depends': [
        'sale', 
        'sh_sale_reports',
        'setu_rfm_analysis',
        'general_template',
        'ks_sales_forecast',
        'ks_dashboard_ninja',
        'equip3_sale_other_operation',
        'blanket_sale_order_app',
        'equip3_general_setting'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/menu_icons.xml',
        'views/sale_order_view.xml',
        'views/sale_report_views.xml',
        'views/sale_report_margin_view.xml',
        'views/rfm_segment_view.xml',
        'views/template_sales_margin.xml',
        'views/sale_invoice_summary_view.xml',
        'views/customer_sale_analysis_view.xml',
        'views/sale_product_profit_view.xml',
        'views/sales_product_indent_view.xml',
        'views/sales_by_product_category_view.xml',
        'views/sh_tsp_top_selling_product.xml',
        'views/sh_top_cutsomers_views.xml',
        'report/sale_order_day_wise_report.xml',
        'report/sale_detail_report.xml',
        'report/sale_report_by_saleperson.xml',
        'report/sale_invoice_summary_report.xml',
        'report/sale_invoice_payment_report.xml',
        'report/customer_sales_analysis_report.xml',
        'report/top_customer_report.xml',
        'report/top_product_report.xml',
        'report/sale_product_profit_report.xml',
        'report/sale_by_product_category_report.xml',
        'report/sale_product_indent_report.xml',
        'data/ks_quotation_data.xml',
        'data/ks_sale_data.xml',
    ],
    # only loaded in demonstration mode

    'auto_install': True,

    'demo': [

    ],
}
