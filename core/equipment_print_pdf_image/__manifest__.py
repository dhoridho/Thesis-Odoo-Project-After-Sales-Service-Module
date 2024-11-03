# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': "Equipment Images and PDF Report",
    'version': '2.1.3',
    'license': 'Other proprietary',
    'price': 13.0,
    'currency': 'EUR',
    'summary':  """Maintenance Equipment Images and PDF Report""",
    'description': """
This apps allow you to Print PDF Report for Equipment Image.
Equipment Images and PDF Report
Maintenance equipment
    """,
    'author': "Probuse Consulting Service Pvt. Ltd.",
    'website': "http://www.probuse.com",
    'support': 'contact@probuse.com',
    'images': ['static/description/img66.jpg'],
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/equipment_print_pdf_image/868',#'https://youtu.be/dlteFdePDLk',
    'category': 'Operations/Maintenance',
    'depends': ['maintenance'],
    'data': [
           'views/maintenance_views.xml',
           'views/maintenance_equipment_report_view.xml'
            ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
