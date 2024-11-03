# -*- coding: utf-8 -*-
{
    'name': 'eLearning with Scorm',
    'version': '1.2',
    'sequence': 10,
    'summary': 'Enhanced learning using Scorm integration',
    'website': 'https://www.manprax.com',
    'author': 'ManpraX Software LLP',
    'category': 'Website/eLearning',
    'description': """
Create Online Courses Using Scorm
""",
    'depends': [
        'website_slides',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/slide_slide_views.xml',
        'views/templates.xml',
    ],
    'demo': [],
    'qweb': [],
    'images': ["static/description/images/scorm_banner.png"],
    'installable': True,
    'application': True,
    'license': 'AGPL-3',
}
