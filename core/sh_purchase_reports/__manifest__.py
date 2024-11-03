# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "All In One Purchase Reports",
    "author": "Softhealer Technologies",
    "license": "OPL-1",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Purchases",
    "summary": "Purchase Report Based On Analysis, Compare Vendors By Purchase Report Module, Compare Products Based On Purchase, Purchase Representative Wise Payment Report, Purchase Report By Vendor, Purchase Report By Tax, Purchase Report By Date And Time Odoo",
    "description": """All in one purchase report useful to provide different purchases and bill reports to do analysis. A purchase analysis report shows the trends that occur in a company's purchase volume over time. In its most basic form, a purchase analysis report shows whether purchases are increasing or declining. At any time during the fiscal year, purchase managers may analyze the trends in the report to determine the best course of action. Purchase reports are a record of purchase activity over a particular period.""",
    "version": "1.1.2",
    "depends": [
                "purchase",
                "account",
    ],
    "application": True,
    "data": [
        "sh_day_wise_purchase/security/ir.model.access.csv",
        "sh_day_wise_purchase/wizard/purchase_order_day_wise_wizard.xml",
        "sh_day_wise_purchase/report/purchase_order_day_wise_report.xml",
        "sh_day_wise_purchase/report/report_xlsx_view.xml",

        "sh_payment_purchase_report/security/payment_report_security.xml",
        "sh_payment_purchase_report/security/ir.model.access.csv",
        "sh_payment_purchase_report/wizard/payment_report_wizard.xml",
        "sh_payment_purchase_report/report/payment_report.xml",
        "sh_payment_purchase_report/wizard/xls_report_view.xml",

        "sh_purchase_details_report/security/ir.model.access.csv",
        "sh_purchase_details_report/wizard/purchase_details_report_wizard.xml",
        "sh_purchase_details_report/report/purchase_details_report.xml",
        "sh_purchase_details_report/report/report_xlsx_view.xml",

        "sh_purchase_report_pr/security/ir.model.access.csv",
        "sh_purchase_report_pr/wizard/report_representative_wizard.xml",
        "sh_purchase_report_pr/views/xls_report_view.xml",
        "sh_purchase_report_pr/report/representative_report.xml",

        "sh_top_purchasing_product/security/ir.model.access.csv",
        "sh_top_purchasing_product/wizard/top_purchasing_wizard.xml",
        "sh_top_purchasing_product/views/top_purchasing_view.xml",
        "sh_top_purchasing_product/report/top_purchasing_product_report.xml",
        "sh_top_purchasing_product/report/report_xlsx_view.xml",

        "sh_top_vendor/security/ir.model.access.csv",
        "sh_top_vendor/wizard/top_vendor_wizard.xml",
        "sh_top_vendor/report/top_vendor_report.xml",
        "sh_top_vendor/report/report_xlsx_view.xml",

        "sh_vendor_purchase_analysis/security/ir.model.access.csv",
        "sh_vendor_purchase_analysis/report/report_purchase_analysis.xml",
        "sh_vendor_purchase_analysis/wizard/vendor_purchase_analysis_wizard.xml",
        "sh_vendor_purchase_analysis/report/report_purchase_analysis_xls_view.xml",

        "sh_purchase_by_category/security/ir.model.access.csv",
        "sh_purchase_by_category/report/report_purchase_by_category.xml",
        "sh_purchase_by_category/wizard/purchase_by_category_wizard.xml",
        "sh_purchase_by_category/report/report_purchase_category_xls_view.xml",

        "sh_product_purchase_indent/security/ir.model.access.csv",
        "sh_product_purchase_indent/report/report_purchase_product_indent.xml",
        "sh_product_purchase_indent/wizard/purchase_product_indent_wizard.xml",
        "sh_product_purchase_indent/report/report_purchase_product_indent_xls_view.xml",

        "sh_purchase_bill_summary/security/ir.model.access.csv",
        "sh_purchase_bill_summary/report/report_purchase_bill_summary.xml",
        "sh_purchase_bill_summary/wizard/purchase_bill_summary_wizard.xml",
        "sh_purchase_bill_summary/report/report_purchase_bill_summary_xls_view.xml",

        "sh_purchase_product_profit/security/ir.model.access.csv",
        "sh_purchase_product_profit/report/report_purchase_product_profit.xml",
        "sh_purchase_product_profit/wizard/purchase_product_profit_wizard.xml",
        "sh_purchase_product_profit/report/report_purchase_product_profit_xls_view.xml",

    ],

    "images": ["static/description/background.gif", ],
    "auto_install": False,
    "installable": True,
    "price": "100",
    "currency": "EUR"
}
