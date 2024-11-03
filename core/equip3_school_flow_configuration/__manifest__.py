# -*- coding: utf-8 -*-
{
    'name': "School Configuration",

    'summary': """
    School Configuration
    """,
    'author': "Braincrew Apps",
    'version': '1.1.11',
    'depends': ['school', 'web', 'exam', 'equip3_school_operation'],

    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'wizard/school_flow_wizard_views.xml',
        'wizard/class_flow_wizard_views.xml',
        'wizard/ems_flow_views.xml',
    ],
    'qweb': [
        'static/src/xml/ems_flow.xml',
        'static/src/xml/class_flow.xml',
    ],
    'installable': True,
    'application': False,
}
