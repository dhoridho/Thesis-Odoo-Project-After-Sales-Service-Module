{
    'name': 'Order Display',
    'version': '1.1.3',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'http://www.pragtech.co.in',
    'category': 'Website',
    'summary': 'Orders processing system for restaurant, shipping, ecommerce industries etc.',
    'description': """
Odoo Order Display System
=========================
This module is used to manage sale orders through web interface. List of features as below:

Features:
---------
    * Real time orders loading on display system.
    * Real time order processing by users.

    """,
    'depends': ['website', 'sale'],
    'data': [
        'security/res_groups.xml',
        # 'data/order_data.xml',
        # 'security/ir.model.access.csv',
        'views/templates.xml',
        'views/order_display.xml',
        'views/order_display_views.xml',
    ],
    'images': ['static/description/order-display.gif'],
    'currency': 'USD',
    'license': 'OPL-1',
    'price': 299.00,
    'installable': True,
    'application': True,
    'auto_install': False,
}
