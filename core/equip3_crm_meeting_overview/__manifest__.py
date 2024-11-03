# -*- coding: utf-8 -*-
{
    'name': "Meeting Calendar Overview",
    'summary': """
        Meeting Calendar Overview """,
    'description': """
        This module manages these features :
        Meeting Calendar Overview
    """,
    'author': "Hashmicro",
    'website': 'www.hashmicro.com',
    'category': 'CRM',
    'version': '1.1.6',
    'depends': [
        'base',
        'calendar',
        'crm',
        'equip3_crm_operation',
        'equip3_sale_accessright_setting'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/meeting_overview_security.xml',
        'views/meeting_overview_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
