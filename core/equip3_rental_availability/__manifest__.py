# -*- coding: utf-8 -*-
{
    'name': "equip3_rental_availability",

    'summary': """
        Manage Product Rental Availability""",

    'description': """
        This module manages these features:
        1. Product Rental Availability
    """,

    'author': "Hashmicro / Yusup Firmansyah",
    'website': "https://www.hashmicro.com/id/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales/Sales',
    'version': '1.1.9',

    # any module necessary for this one to work correctly
    'depends': ['base','browseinfo_rental_management','sales_team','equip3_rental_operation','ks_gantt_view_base'],

    # always loaded
    'data': [
        # 'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/rental_booking.xml',
        'views/rental_schedule_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
