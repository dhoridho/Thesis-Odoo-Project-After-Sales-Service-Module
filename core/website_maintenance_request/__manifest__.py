# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Maintenance Request from Website by Customer',
    'version': '2.2.3',
    'price': 49.0,
    'currency': 'EUR',
    'images': ['static/description/image.jpg'],
    'license': 'Other proprietary',
    'category': 'Human Resources',
    'summary': 'Allow user to send maintenance request by website',
    'description': """
    
This module allow user to send maintenance request and also send email.
Maintenance Request
Equipments Maintenance Request
Equipments
Maintenance Request
Maintenance Equipment
Equipment Maintenance
product Maintenance
asset Maintenance
company Maintenance
Maintenance Equipments
print maintenance request
maintenance request report
maintenance request pdf
maintenance request qweb
equipment request
Maintenance Request From Website
Maintenance Request Page
Page on Website For Maintenance Request
Maintenance Request in Backend (Odoo Standard)
Maintenance Stage
maintenance team
maintenance duration 
maintenance request
Maintenance Teams
Track equipment and manage maintenance requests
manage maintenance requests
Track equipment


            """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'www.probuse.com',
    'support': 'contact@probuse.com',
    'images': ['static/description/1webmaint_request.png'],
    # 'live_test_url': 'https://youtu.be/dbxpZg0WxHU',
    # 'live_test_url' : 'https://youtu.be/anDwFpPsLLw',
    'live_test_url' : 'http://probuseappdemo.com/probuse_apps/website_maintenance_request/354',#'https://youtu.be/vD3XV1LMFAc',
    'depends': [
        'website',
        'maintenance'
        ],
    'data': [
            'views/mail_template.xml',
            'views/maintenance_support_request_template.xml',
             ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
