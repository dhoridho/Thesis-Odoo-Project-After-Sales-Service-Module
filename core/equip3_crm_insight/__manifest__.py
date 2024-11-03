# -*- encoding: utf-8 -*-

{
    "name" : "CRM Insight",
    'version': '14.0.1.0.1',
    "author" : "Hashmicro",
    'website' : 'https://hashmicro.com/',
    "category" : "Sales",
    'summary': """Detailed Dashboard View for CRM""",
    "depends" : ["base", 'sale_management', 'crm'],
    "init_xml" : [],
    "demo_xml" : [],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_view.xml',
        'views/assets.xml',
        'views/crm_insight_views.xml'
    ],
    'qweb': [
        'static/src/xml/dashboard_view.xml',
        # 'static/src/xml/sub_dashboard.xml',
        'static/src/xml/crm_insight.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
