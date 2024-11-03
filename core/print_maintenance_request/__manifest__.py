# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Print Maintenance Request PDF',
    'version': '1.1.1',
    'price': 10.0,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'category': 'Operations/Maintenance',
    'summary': 'This module allow user to print maintenance request in pdf format.',
    'description': """
Tags:
print maintenance request
maintenance request report
maintenance request pdf
maintenance request qweb
equipment request
            """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'www.probuse.com',
    'support': 'contact@probuse.com',
    'images': ['static/description/img1.jpg'],
    'live_test_url': 'http://probuseappdemo.com/probuse_apps/print_maintenance_request/393',#'https://youtu.be/bi743nRWVQQ',
    'depends': ['maintenance'],
    'data': ['view/report_reg.xml',
             'view/maintenance_report_view.xml',
             ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
