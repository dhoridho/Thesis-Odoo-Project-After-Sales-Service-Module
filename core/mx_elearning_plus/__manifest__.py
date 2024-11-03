# -*- coding: utf-8 -*-
{
    'name': 'eLearning Plus',
    'version': '1.1.1',
    'sequence': 10,
    'summary': 'Added extra features to enhance learning.',
    'website': 'https://www.manprax.com',
    'author': 'ManpraX Software LLP',
    'category': 'Website/eLearning',
    'description': """
Extended feature of elearning.
""",
    'depends': [
        'website_slides',
    ],
    'data': [
        'views/assets.xml',
        'views/slide_view.xml',
        'views/website_slides_templates_course.xml',
    ],
    'demo': [],
    'qweb': [],
    'images': ["static/description/images/app_banner_plus.png"],
    'installable': True,
    'application': True,
    'license': 'AGPL-3',
}
