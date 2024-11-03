# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Cash Forecasting',
    'version': '1.1.5',
    'price': 279,
    'currency': 'EUR',
    'category': 'account',
    'summary': """ 
        The cash Forecast solution calculates and allows end users to know the available cash 
        in the upcoming future considering the Opening balance, all cash receipts, and all cash expenditures.
        cash forecasting, cash flow forecasting, cash in, cash out, expense, forecast budget, liquidity risk management,
        cash needs, inflow, outflow, payment, in payment, out payment, chart of accounts, forecast finance, forecast cash flow,
        net income, depreciation, inventory, receivable, payable, fixed asset, opening balance, closing balance,
        income, expenses, net forecast, total cash in, total cash out, opening forecast, closing forecast, recurring forecast, real forecast,
        cash forecast analysis, treasure, cash analytic, advance cash planning, cash capital, cashin, cashout,
        treasury analysis, cashflow management, cash flow management, assests 
        """,
    'description': """
        The cash Forecast solution calculates and allows end users to know the available cash 
        in the upcoming future considering the Opening balance, all cash receipts, and all cash expenditures. 
        Also, various statistical and analytical reports allow users to have a complete insight into 
        all income and expenditures for each period.
    """,
    'website': 'https://www.setuconsulting.com',
    'support': 'support@setuconsulting.com',
    'images': ['static/description/banner.gif'],
    'depends': ['account', 'sale', 'sh_sync_fiscal_year'],
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'license': 'OPL-1',
    'sequence': 20,
    'data': [
        'security/security.xml',
        'views/assets.xml',
        'security/ir.model.access.csv',
        'views/setu_cash_forecast_group.xml',
        'views/setu_cash_forecast_type.xml',
        'views/cash_forecast_tag.xml',
        # 'views/setu_cash_forecast_calculation.xml',
        'views/cash_forecast_fiscal_year.xml',
        'views/setu_cash_forecast_dashboard_menu.xml',
        'views/create_update_cash_forecast.xml',
        'views/setu_cash_forecast.xml',
        'views/setu_cash_forecast_report_view.xml',
        'views/account_account_view.xml',
        'data/setu_cash_forecast_actual_value_cron.xml',
        'data/demo_data.xml',
        'views/menu_category.xml'
    ],
    'qweb': [
            'static/src/xml/*',
    ],
    'application': True,
    'live_test_url': 'https://www.youtube.com/playlist?list=PLH6xCEY0yCIB-k1yPvSZHhZEsqVYE0evq',
}
