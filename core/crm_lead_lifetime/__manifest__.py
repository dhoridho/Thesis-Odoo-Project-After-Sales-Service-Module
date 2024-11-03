# -*- coding: utf-8 -*-
{
    'name': "CRM Lead Lifetime",
    'version': '1.1.1',
    'license': 'OPL-1' ,
    'summary': """Track CRM Lead Lifetime""",
    'description': 
    """CRM Lead Lifetime app presents vital information and report about the lead's lifetime. 
    In CRM leads have to pass by stages. And we need to track time spent by leads on each stages.
    In this case our app will help to identify all these questions. Users are given full power of filters and they can explore around data using filters on Lead's lifetime report
        """,
    'author': "SunArc Technologies",
    'website': "https://www.suncartstore.com/odoo-apps/crm-lead-lifetime",
    'sequence': 1,
    'category': 'Sales',
    'price': 49,
    'currency' : 'EUR',

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/crm_lead_age.xml',
        'data/lead_age_group.xml',
        'report/lead_age_report.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'images':  ['static/description/Banner.png'],

}
