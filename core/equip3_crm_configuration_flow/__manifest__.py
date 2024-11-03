# -*- coding: utf-8 -*-
{
    'name': "CRM Configuration Flow",

    'summary': """
    CRM Configuration
    """,
    'author': "",
    'version': '1.1.9',
    'depends': ['base', 'equip3_crm_operation', 'equip3_crm_report'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/crm_flow_wizard_views.xml',
        'wizard/assets.xml',
    ],

    'qweb': [
        'static/src/xml/crm_configuration_flow.xml'
    ],

    'installable': True,
    'application': False,
}