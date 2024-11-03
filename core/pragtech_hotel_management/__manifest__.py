{
    'name': 'Hotel Management',
    'version': '1.1.1',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'www.pragtech.co.in',
    'summary': 'Hotel Management Module for Hotel/Resort/Property management. You can manage Configure Property Hotel Configuration Check In, Check out Manage Folio',
    "description": """
Module for Hotel/Resort/Property management. You can manage:
    * Configure Property
    * Hotel Configuration
    * Check In, Check out
    * Manage Folio
    * Payment

Different reports are also provided, mainly for hotel statistics.
""",
    "depends": ['base', 'stock', 'product', 'mrp', 'point_of_sale', 'web', 'website', 'payment'],
    "category": "Generic Modules",
    'currency': 'USD',
    'price': 499,
    'images': ['static/description/img/Animated-odoo-hotel-management.gif'],
    #'images': ['static/description/end-of-year-sale-main.jpg'],
    'live_test_url': 'https://www.pragtech.co.in/company/proposal-form.html?id=103&name=Odoo-Hotel-Management',
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}
