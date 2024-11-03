# -*- coding: utf-8 -*-
{
    'name': "Equip3 CRM Tracking",
    'summary': """
        Salesperson Tracking data entry and display history """,
    'description': """
        This module manages these features :
        1. Salesperson GPS Tracking history from crm-apps
    """,
    'author': "Hashmicro",
    'website': 'www.hashmicro.com',
    'category': 'CRM',
    'version': '1.1.9',
    'depends': [
        'web',
        'base',
        'crm',
        'base_setup',
        'base_geolocalize'
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/crm_sales_tracking_history_report.xml',
        'views/assets.xml',
        'views/crm_tracking_views.xml',
        'views/crm_tracking_history_views.xml',
        'wizards/tracking_report_views.xml',
        'wizards/crm_sales_tracking_history_views.xml',
        'views/menu.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
