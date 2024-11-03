# -*- coding: utf-8 -*-

{
    "name": "Equip 3 - Mining Reports",
    "version": "1.1.19",
    "category": "",
    "summary": "Equip 3 - Mining Reports",
    "description": """Equip 3 - Mining Reports""",
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    "depends": [
        'equip3_mining_operations',
        'ks_dashboard_ninja'
    ],
    "data": [
        'security/ir.model.access.csv',
        'security/mining_report_ir.xml',
        'data/ks_mining_dashboard_data.xml',
        'views/assets.xml',
        'views/mining_flow.xml',
        'views/product_template_views.xml',
        'views/stripping_ratio_views.xml',
        'views/res_config_settings_views.xml',
        'views/cost_actualization_views.xml',
        'views/mining_production_record_views.xml',
        'views/mining_gis_views.xml',
        'reports/asset_report_views.xml',
        'reports/production_report_views.xml',
        'reports/stripping_ratio_report_views.xml',
        'reports/fuel_ratio_report_views.xml',
        'reports/assets_efficiency_report_views.xml',
        'views/menuitems.xml',
        'views/icon_menu.xml'
    ],
    "qweb": [
        'static/src/xml/mining_flow.xml',
        'static/src/xml/production_report.xml',
        'static/src/xml/asset_report.xml',
        'static/src/xml/stripping_ratio_report.xml',
        'static/src/xml/fuel_ratio_report.xml',
        'static/src/xml/assets_efficiency_report.xml',
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
