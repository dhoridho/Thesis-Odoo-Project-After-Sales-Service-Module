# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

{
    'name': 'Purchase Team',
    'version': '1.1.1',
    'sequence': 1,
    'category': 'Purchases',
    'description':
        """
       Odoo app will allow to add purchase team on RFQ and Purchase Order
Purchase Team
odoo purchase team
odoo purchase team
purchase team
Purchase Team
Odoo Purchase Team
Manage Purchase Team
Odoo manage Purchase Team
Purchase Team Management
Odoo Purchase Team Management
odoo applicatation will allow to add Purchase Team on Request for qutation and purchase order. Purchase team filter into purchase anaylsis pivot view.
odoo app will allow to add Purchase Team on Request for qutation and purchase order. Purchase team filter into purchase anaylsis pivot view.
Manage odoo applicatation will allow to add Purchase Team on Request for qutation and purchase order. Purchase team filter into purchase anaylsis pivot view.
Odoo Manage odoo applicatation will allow to add Purchase Team on Request for qutation and purchase order. Purchase team filter into purchase anaylsis pivot view.
Purchase Manager to create purchase team in purchase configuration
Odoo Purchase Manager to create purchase team in purchase configuration
Manage Purchase Manager to create purchase team in purchase configuration
Odoo Manage Purchase Manager to create purchase team in purchase configuration
Add Purchase Team in RFQ and Purchase order
Odoo Add Purchase Team in RFQ and Purchase order
Manage Add Purchase Team in RFQ and Purchase order
Odoo Manage Add Purchase Team in RFQ and Purchase order
Filter Purchase Analysis Report based on Purchase Team
Odoo Filter Purchase Analysis Report based on Purchase Team
Manage Filter Purchase Analysis Report based on Purchase Team
Odoo Manage Filter Purchase Analysis Report based on Purchase Team
Add Purchase Team
Odoo Add Purchase Team
Manage Add Purchase Team
Odoo Manage Add Purchase Team
Add Purchase Team in Purchase Order
Odoo Add Purchase Team in Purchase Order
Manage Add Purchase Team in Purchase Order
Odoo Manage Add Purchase Team in Purchase Order
Filter Purchase Analysis Report 
Odoo Filter Purchase Analysis Report 
Manage Filter Purchase Analysis Report 
Odoo Manage Filter Purchase Analysis Report 
Filter Purchase Analysis Report Based on Purchase Team
Odoo Filter Purchase Analysis Report Based on Purchase Team
Manage Filter Purchase Analysis Report Based on Purchase Team
Odoo Manage Filter Purchase Analysis Report Based on Purchase Team
Graph Report based on Purchase Team
Odoo Graph Report based on Purchase Team
Manage Graph Report based on Purchase Team
Odoo Manage Graph Report based on Purchase Team
Purchase Graph Report
Odoo Purchase Graph Report
Manage Odoo Purchase Graph Report
Manage Purchase Graph Report
    """,
    'summary': 'Odoo app allow to Add Purchase Team on RFQ and Purchase Order,Purchase Team',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/dev_purchase_team_views.xml',
        'views/purchase_views.xml'
        ],
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    
    # author and support Details =============#
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'website': 'http://www.devintellecs.com',    
    'maintainer': 'DevIntelle Consulting Service Pvt.Ltd', 
    'support': 'devintelle@gmail.com',
    'price':15.0,
    'currency':'EUR',
    #'live_test_url':'https://youtu.be/A5kEBboAh_k',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
