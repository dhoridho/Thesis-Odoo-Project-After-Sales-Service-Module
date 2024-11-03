# -*- coding: utf-8 -*-
{
    'name': "Website Booking in odoo,Website Appointment Booking in odoo, calendar booking slot in odoo",
    'summary': """
        Website Booking in odoo 14, 13, 12, Website Booking, calendar booking slot """,
    'description': """
       Website Booking in odoo 14, 13, 12, Website Booking, calendar booking slot """,
    'category': 'website',
    'version': '14.0.1.1.0',
    # any module necessary for this one to work correctly
    'depends': ['base','calendar','account','crm','contacts',
                'website','website_sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/website_calendar_data.xml',
        'views/assets.xml',
        'views/portal_templates_view.xml',
        'views/portal_appointment_templates.xml',
        'views/appointment_views.xml',
        'views/menu_dashboard_view.xml',
        'views/website.xml',
        'views/website_view.xml',
        'views/appointment_source_views.xml',
        'views/appointee_views.xml',
        'views/appointment_group_views.xml',
        'views/appointment_timeslot_views.xml',
        'views/calendar_appointment_views.xml',
    ],
    'qweb': ["static/src/xml/appointment_dashboard.xml",
             ],

    'price': 145.00,
    'currency': 'USD',
    'support': 'business@axistechnolabs.com',
    'author': 'Axis Technolabs',
    'website': 'http://www.axistechnolabs.com',
    'installable': True,
    'license': 'AGPL-3',
    'images': ['static/description/images/banner.jpg'],

}
