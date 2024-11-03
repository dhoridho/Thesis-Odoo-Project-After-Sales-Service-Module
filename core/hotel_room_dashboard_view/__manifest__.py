# -*- coding: utf-8 -*-


{
    'name': 'Hotel Room Dashboard View',
    'version': '1.10',
    'category': 'General',
    'sequence': 6,
    'description': """
    """,
    'author': 'Pragmatic Techsoft Pvt. Ltd.',
    'depends': ['hotel_management', 'base'],
    'data': [
        'views/hotel_room_dashboard_view.xml',
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/dashboard.xml',
        'views/hotel_reservation_view.xml',
    ],
    'installable': True,
    'application': True,
    'qweb': ['static/src/xml/base.xml',
             'static/src/xml/template.xml'
             ],
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
