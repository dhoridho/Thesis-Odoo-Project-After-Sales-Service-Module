# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': "Create Sales Quotation from Equipment Maintenance",
    'version': '2.1.3',
    'license': 'Other proprietary',
    'price': 79.0,
    'currency': 'EUR',
    'summary':  """Allows you to create a sales quotation / sales order from equipment maintenance requests.""",
    'description': """

sales order from equipment maintenance requests
aintenance requests from sales order
sales order with maintenance request

    """,
    'author': "Probuse Consulting Service Pvt. Ltd.",
    'website': "http://www.probuse.com",
    'support': 'contact@probuse.com',
    'images': ['static/description/img11.jpg'],
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/equipment_maintenance_sales_order/831',#'https://youtu.be/8F1sAM6PBHk',
    'category': 'Operations/Maintenance',
    'depends': [
                'sale',
                'maintenance'
            ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/maintenance_so_createview.xml',
        'views/maintenance_views.xml',
        'views/sale_view.xml',
            ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
