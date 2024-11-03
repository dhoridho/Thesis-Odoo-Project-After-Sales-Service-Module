# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "All In One Sale Reports",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Sales",
    "summary": """Sales Report Based On Analysis, Compare Customer By Sales Report Module, Compare Products Based On Selling, Salesperson Wise Payment Report, Sales Report By Customer And Sales Person, Sales Report By Tax, All in one sales report Odoo""",
    "description": """ All in one sale report useful to provide different sales and invoice reports to do analysis. A sales analysis report shows the trends that occur in a company's sales volume over time. In its most basic form, a sales analysis report shows whether sales are increasing or declining. At any time during the fiscal year, sales managers may analyze the trends in the report to determine the best course of action. Sales reports are a record of sales activity over a particular period. These reports detail what reps have been up to, reveal whether the team is on track to meet its quota, and alert management to any potential issues.
Sales Report Based On Analysis, Compare Customer By Sales Report Module, Compare Products Based On Selling, Salesperson Wise Payment Report, Sales Report By Customer And Sales Person, Sales Report By Tax, Sale Report By Date And Time Odoo """,
    "version": "1.1.3",
    "depends": [
                "sale_management",
    ],
    "application": True,
    "data": [
        "sh_sale_details_report/security/ir.model.access.csv",
        "sh_sale_details_report/wizard/sale_details_report_wizard.xml",
        "sh_sale_details_report/report/report_xlsx_view.xml",
        "sh_sale_details_report/report/sale_details_report.xml",

        "sh_sale_report_salesperson/security/ir.model.access.csv",
        "sh_sale_report_salesperson/wizard/report_salesperson_wizard.xml",
        "sh_sale_report_salesperson/views/xls_report_view.xml",
        "sh_sale_report_salesperson/report/salesperson_report.xml",

        "sh_top_customers/security/ir.model.access.csv",
        "sh_top_customers/wizard/top_customer_wizard.xml",
        "sh_top_customers/report/report_xlsx_view.xml",
        "sh_top_customers/report/top_customer_report.xml",

        "sh_top_selling_product/security/ir.model.access.csv",
        "sh_top_selling_product/wizard/top_selling_wizard.xml",
        "sh_top_selling_product/views/top_selling_view.xml",
        "sh_top_selling_product/report/report_xlsx_view.xml",
        "sh_top_selling_product/report/top_selling_product_report.xml",

        "sh_payment_report/security/payment_report_security.xml",
        "sh_payment_report/security/ir.model.access.csv",
        "sh_payment_report/wizard/payment_report_wizard.xml",
        "sh_payment_report/wizard/xls_report_view.xml",
        "sh_payment_report/report/payment_report.xml",

        "sh_day_wise_sales/security/ir.model.access.csv",
        "sh_day_wise_sales/wizard/sale_order_day_wise_wizard.xml",
        "sh_day_wise_sales/report/report_xlsx_view.xml",
        "sh_day_wise_sales/report/sale_order_day_wise_report.xml",

        "sh_sale_invoice_summary/security/ir.model.access.csv",
        "sh_sale_invoice_summary/report/report_sale_invoice_summary.xml",
        "sh_sale_invoice_summary/wizard/sale_invoice_summary_wizard.xml",
        "sh_sale_invoice_summary/report/report_sale_invoice_summary_xls_view.xml",

        "sh_customer_sales_analysis/security/ir.model.access.csv",
        "sh_customer_sales_analysis/report/report_sales_analysis.xml",
        "sh_customer_sales_analysis/wizard/customer_sales_analysis_wizard.xml",
        "sh_customer_sales_analysis/report/report_sales_analysis_xls_view.xml",

        "sh_sale_product_profit/security/ir.model.access.csv",
        "sh_sale_product_profit/report/report_sales_product_profit.xml",
        "sh_sale_product_profit/wizard/sales_product_profit_wizard.xml",
        "sh_sale_product_profit/report/report_sales_product_profit_xls_view.xml",

        "sh_sale_by_category/security/ir.model.access.csv",
        "sh_sale_by_category/report/report_sale_by_category.xml",
        "sh_sale_by_category/wizard/sale_by_category_wizard.xml",
        "sh_sale_by_category/report/report_sale_category_xls_view.xml",

        "sh_product_sales_indent/security/ir.model.access.csv",
        "sh_product_sales_indent/report/report_sales_product_indent.xml",
        "sh_product_sales_indent/wizard/sale_product_indent_wizard.xml",
        "sh_product_sales_indent/report/report_sale_product_indent_xls_view.xml",

    ],
    "images": ["static/description/background.gif", ],
    "license": "OPL-1",
    "auto_install": False,
    "installable": True,
    "price": 100,
    "currency": "EUR"
}
