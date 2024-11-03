
{
    'name': 'Configurable Order Stages',
    'version': '1.1.2',
    'summary': """Dynamic order stages on the basis of Warehouse""",
    'description': """
        This module is used to defined generic stages in the order stages master & then that stages linked 
        to warehouses. This linked stages will be used on the order's status bar. 
    """,
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'company': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'http://www.pragtech.co.in',
    'category': 'Sale',
    'depends': ['sale', 'stock', 'sale_stock','pragmatic_delivery_control_app','pragmatic_odoo_website_order_display'],
    'license': 'OPL-1',
    'data': [
        'data/order_stage_data.xml',
        'security/ir.model.access.csv',
        'views/order_stage_views.xml',
        'views/sale_views.xml',
        'views/order_stages.xml',
    ],

    'images': [],
    'currency': 'USD',
    'price': 399.00,
    'installable': True,
    'application': False,
    'auto_install': False,
}
