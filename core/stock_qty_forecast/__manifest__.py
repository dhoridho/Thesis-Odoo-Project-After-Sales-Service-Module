# -*- coding: utf-8 -*-
{
    "name": "Stock Demand Trends and Forecast",
    "version": "14.0.1.0.1",
    "category": "Warehouse",
    "author": "faOtools",
    "website": "https://faotools.com/apps/14.0/stock-demand-trends-and-forecast-547",
    "license": "Other proprietary",
    "application": True,
    "installable": True,
    "auto_install": False,
    "depends": [
        "stock"
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/data.xml",
        "wizard/open_stock_series.xml",
        "views/res_config_settings.xml",
        "views/product_product.xml",
        "views/product_template.xml",
        "views/stock_location.xml",
        "reports/report_stock_demand.xml"
    ],
    "qweb": [
        
    ],
    "js": [
        
    ],
    "demo": [
        
    ],
    "external_dependencies": {
        "python": [
                "pandas",
                "numpy",
                "statsmodels",
                "scipy",
                "xlsxwriter"
        ]
},
    "summary": "The tool to calculate stock demand trends and make prediction for future demand statistically. Stock Forecast",
    "description": """
For the full details look at static/description/index.html

* Features * 

- Statistical methods to forecast stock demand
- Usage requirements



#odootools_proprietary

    """,
    "images": [
        "static/description/main.png"
    ],
    "price": "198.0",
    "currency": "EUR",
    "live_test_url": "https://faotools.com/my/tickets/newticket?&url_app_id=97&ticket_version=14.0&url_type_id=3",
}