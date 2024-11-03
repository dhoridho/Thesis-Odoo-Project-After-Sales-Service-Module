# -*- coding: utf-8 -*-
# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Maintenance Stages Email Response',
    'version': '1.1.1',
    'category': 'Manufacturing/Maintenance',
    'price': 9.0,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'depends': [
        'maintenance','mail'
    ],
    'summary': "Email Template on Maintenance Request Stages",
    'description': """
This app sends auto response email notifications of maintenance 
request form when stages are moving on. 
    """,
    'author': "Probuse Consulting Service Pvt. Ltd.",
    'website': "http://www.probuse.com",
    'live_test_url': 'http://probuseappdemo.com/probuse_apps/maintenance_stages_email_response/310',#'https://youtu.be/64xtthyjU9s',
    'support': 'contact@probuse.com',
    'images': ['static/description/display.jpg'
    ],
    'data': [
        'views/maintenance_views.xml',
        'data/maintenance_mail_template_data.xml',
    ],
    'installable': True,
    'application': False,
}
