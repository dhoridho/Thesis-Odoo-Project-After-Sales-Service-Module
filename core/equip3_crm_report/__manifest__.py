# -*- coding: utf-8 -*-
{
    'name': "Equip3 CRM Report",

    'summary': """
        Manage CRM Reports """,

    'description': """
        This module manages these features :
        1. Leads Analysis
    """,

    'author': "Hashmicro",
    'category': 'CRM',
    'version': '1.1.24',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'ks_dashboard_ninja',
        'equip3_crm_operation',
        'equip3_accounting_operation',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/crm_security.xml',
        'data/ks_crm_data.xml',
        'data/ks_lead_monitoring.xml',
        'views/views.xml',
        "views/calendar_event_views.xml",
        'views/meeting_analysis_report_new_views.xml',
        'views/meeting_analysis_report_views.xml',
        'views/leads_analysis_view.xml',
        'views/menu_icons.xml',
        'views/crm_activity_report_views.xml',
        'views/whatsapp_template.xml',
        'views/crm_target_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}