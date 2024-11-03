# -*- coding: utf-8 -*-
###################################################################################
#
#    inteslar software trading llc.
#    Copyright (C) 2018-TODAY inteslar software trading llc (<https://www.inteslar.com>).
#
###################################################################################
{
    'name': "Employee Performance Evaluation",
    'version': '1.1.2',
    'category': 'HR',
    'price':   700.00,
    'currency': 'EUR',
    'maintainer': 'inteslar',
    'website': "https://www.inteslar.com",
    'license': 'OPL-1',
    'author': 'inteslar',
    'summary': 'Employee Performance Evaluation From Website',
    'images': ['static/images/main_screenshot.png'],
    'depends': ['resource', 'hr','web', 'portal','website','account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/performance_view.xml',
        'views/portal_performance_templates.xml',
        'views/portal_teamperformance_templates.xml',
    ],
    'installable': True,
    'application': True,
}