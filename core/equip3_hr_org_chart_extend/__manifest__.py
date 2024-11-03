# -*- coding: utf-8 -*-
{
    'name': 'Filters : Equip3 Organization Chart',
    'author': 'Maulik (Braincrew Apps)',
    'website': "https://antsyz.com",
    'version': '1.1.2',
    'summary': 'Add Filters for Employee Hierarchy Chart View',
    'depends': ['org_chart_premium'],
    'category': 'Human Resources',
    'data': [
        'views/chart_extend_asset.xml',
    ],
    'qweb': [
        "static/src/xml/org_chart_title.xml",
    ],
    'installable': True,
    'application': True,
}
