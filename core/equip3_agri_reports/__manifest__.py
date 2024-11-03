# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip 3 - Agriculture Reports',
    'author': 'Hashmicro',
    'version': '1.1.2',
    'category': 'Agriculture',
    'summary': 'Equip 3 - Agriculture Reports',
    'description': '''''',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'equip3_agri_operations',
        'ks_dashboard_ninja'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/ks_agriculture_dashboard_data.xml',
        'views/assets.xml',
        'views/gis_views.xml',
        'views/activity_overview_views.xml',
        'views/budget_planning_views.xml',
        'views/budget_planning_block_views.xml',
        'views/res_config_settings_views.xml',
        'reports/material_usage_report_views.xml',
        'reports/finished_good_report_views.xml',
        'reports/harvesting_analysis_report_views.xml',
        'reports/harvesting_monthly_report_views.xml',
        'reports/budget_analysis_report_views.xml',
        'reports/nursery_report_views.xml',
        'reports/harvesting_report_views.xml',
        'reports/Immature_cost_report_views.xml',
        'reports/mature_cost_report_views.xml',
        'reports/budget_planning_report_views.xml',
        'reports/budget_planning_block_report_views.xml',
        'reports/nursery_yield_report_views.xml',
        'views/menuitems.xml',
    ],
    'qweb': [
        'static/src/xml/agriculture_flow.xml',
        'static/src/xml/harvesting_analysis_report.xml',
        'static/src/xml/harvesting_monthly_report.xml',
        'static/src/xml/budget_analysis_report.xml',
        'static/src/xml/list_view_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
