# -*- coding: utf-8 -*-
{
    "name": "KPI Balanced Scorecard",
    "version": "14.0.1.0.4",
    "category": "Extra Tools",
    "author": "faOtools",
    "website": "https://faotools.com/apps/14.0/kpi-balanced-scorecard-492",
    "license": "Other proprietary",
    "application": True,
    "installable": True,
    "auto_install": True,
    "depends": [
        "mail"
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/data.xml",
        "data/cron.xml",
        "views/views.xml",
        "wizard/kpi_copy_template.xml",
        "views/kpi_measure_item.xml",
        "views/kpi_measure.xml",
        "views/kpi_constant.xml",
        "views/kpi_item.xml",
        "views/kpi_period.xml",
        "views/kpi_category.xml",
        "views/kpi_scorecard_line.xml",
        "views/res_config_settings.xml",
        "views/menu.xml",
        "data/crm_measures.xml",
        "data/sale_measures.xml",
        "data/invoice_measures.xml",
        "data/project_measures.xml"
    ],
    "qweb": [
        "static/src/xml/*.xml"
    ],
    "js": [
        
    ],
    "demo": [
        
    ],
    "external_dependencies": {},
    "summary": "The tool to set up KPI targets and control their fulfillment by periods",
    "description": """
For the full details look at static/description/index.html

* Features * 

- Real-time control and historical trends
- Drag-and-drop formulas for KPIs
- Shared KPIs and self-control
- KPI settings to process Odoo data



#odootools_proprietary

    """,
    "images": [
        "static/description/main.png"
    ],
    "price": "198.0",
    "currency": "EUR",
    "live_test_url": "https://faotools.com/my/tickets/newticket?&url_app_id=138&ticket_version=14.0&url_type_id=3",
}