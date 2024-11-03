# -- coding: utf-8 --
{
    'name': "Sales Forecast",

    'summary': """
        Sales Forecast v14.0""",

    'description': """
              Sales Forecast for odoo 14.0.
              Best Sales Forecast Apps
              Sales Forecast Apps
              Odoo Forecast Apps
              Sales Trends
              Sales Trends and Forecast
              Sales Predict Apps
              Sales Prediction Apps
              Predict Sales Apps
              Calculate Sales Trends
              Forecast Future Sales Statistic
              Sales Trends Chart
              Sales Forecast Chart
              Stock Demand Trends
              Stock Demand Forecast Apps
              Machine Learning Apps
              Data Prediction Apps
              Data Forecast Apps
              Time Series Forecasting Apps
              Pre Month Sale
              Future Sale App
              Future Sales Prediction App
              Stock forecast analysis
              Contract Forecast
              Budget Commitment Forecast
              Inventory Forecast Apps
              Stock Analysis Forecast
              Auto Arima Apps
              Budget Preparing Apps
              Budget Forecast Apps
              Expenditure Forecast Apps
              Stock Forecast Apps
              Stock Planning Apps
              Warehouse forecast Apps
              Sales Department Apps
              Sales Performance Control Apps
              Historical Data Prediction Apps
              Seasonal Sale Prediction Apps
              Machine Learning Libraries Apps
              Precise Data Apps
              Sales Trends Apps
              Sales Tracking Apps
              Autoregression Apps
              ARIMA Apps
              Library Apps
              MR-AR Apps
              AR Apps
              Purchase Forecast Apps
              Account Treasury Forecast Apps
              Treasury Forecast Apps
              Moving Average Apps
              Autoregressive Moving Average Apps
              Autoregressive Integrated Moving Average Apps
              Vector Autoregression Apps
              Simple Exponential Smoothing Apps
              Forecast Analysis Report Apps
      """,
    'author': "Ksolves India Ltd.",
    'website': "https://www.ksolves.com/",
    'license': 'OPL-1',
    'currency': 'EUR',
    'price': 209,
    'live_test_url': 'https://salesforecast.kappso.com/web/demo_login',
    'category': 'Tools',
    'support': 'sales@ksolves.com',
    'version': '1.1.1',
    'images': [
        'static/description/sales_forecast.gif'
    ],
    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'sale_management', 'sale'],
    'external_dependencies': {
        'python': ['numpy', 'scipy', 'setuptools', 'pmdarima'],
    },

    # always loaded
    'data': [
        'security/ks_security.xml',
        'security/ir.model.access.csv',
        'data/ks_forecast_sequence.xml',
        'views/ks_assets.xml',
        'views/ks_forecast_view.xml',
        'views/ks_forecast_result_view.xml',
        'views/ks_res_config_view.xml',
        'views/ks_message_wizard_view.xml',
        'wizards/ks_tuning_wizard_views.xml',
    ],
}
# -*- coding: utf-8 -*-
