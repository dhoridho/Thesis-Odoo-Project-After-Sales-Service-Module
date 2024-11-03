# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 Purchase Report',
    'version': '1.1.33',
    'summary': 'Manage your Purchase Requests and Purchase Orders Report Analysis',
    'depends': ['purchase','purchase_request','sh_purchase_reports','equip3_purchase_operation','equip3_purchase_masterdata','xf_purchase_dashboard','ks_dashboard_ninja','sh_po_tender_management','vendor_evaluation','equip3_general_setting'],
    'category': 'Purchase/Purchase',
    'data': [
        'data/ks_purchase_dash.xml',
        'data/ir_rule.xml',
        'security/ir.model.access.csv',
        "wizard/purchase_order_day_wise_wizard.xml",
        'report/purchase_analysis_report_view.xml',
        'report/report_purchase_bill_summary.xml',
        "report/purchase_details_report.xml",
        "report/representative_report.xml",
        "report/top_purchasing_product_report.xml",
        "report/report_purchase_product_profit.xml",
        "report/report_purchase_by_category.xml",
        "report/report_purchase_analysis.xml",
        "report/top_vendor_report.xml",
        "report/payment_report.xml",
        "report/report_purchase_product_indent.xml",
        "report/purchase_order_day_wise_report.xml",
        "views/assets.xml",
        'views/menu_icons.xml',
        'views/purchase_order_view.xml',
        'views/purchase_report_view.xml',
        'views/vendor_rating_view.xml',
        'views/purchase_team_analysis.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}