# -*- coding: utf-8 -*-
#╔══════════════════════════════════════════════════════════════════════╗
#║                                                                      ║
#║                  ╔═══╦╗       ╔╗  ╔╗     ╔═══╦═══╗                   ║
#║                  ║╔═╗║║       ║║ ╔╝╚╗    ║╔═╗║╔═╗║                   ║
#║                  ║║ ║║║╔╗╔╦╦══╣╚═╬╗╔╬╗ ╔╗║║ ╚╣╚══╗                   ║
#║                  ║╚═╝║║║╚╝╠╣╔╗║╔╗║║║║║ ║║║║ ╔╬══╗║                   ║
#║                  ║╔═╗║╚╣║║║║╚╝║║║║║╚╣╚═╝║║╚═╝║╚═╝║                   ║
#║                  ╚╝ ╚╩═╩╩╩╩╩═╗╠╝╚╝╚═╩═╗╔╝╚═══╩═══╝                   ║
#║                            ╔═╝║     ╔═╝║                             ║
#║                            ╚══╝     ╚══╝                             ║
#║                  SOFTWARE DEVELOPED AND SUPPORTED BY                 ║
#║                ALMIGHTY CONSULTING SOLUTIONS PVT. LTD.               ║
#║                      COPYRIGHT (C) 2016 - TODAY                      ║
#║                      https://www.almightycs.com                      ║
#║                                                                      ║
#╚══════════════════════════════════════════════════════════════════════╝
{
    "name": "ACS HMS Dashboards", 
    "summary": "HMS Dashboard for users. Separte deashboard detials for doctor, receptionist and admin user so they can get thier related infrmation and statistics from single view",
    "description": """HMS Dashboard for users. Separte deashboard detials for doctor, receptionist and admin user so they can get thier related infrmation and statistics from single view.
        Hospital Management System hospital dashboard physician dashboard admin dashboard ACS HMS
    """, 
    'version': '1.0.5',
    'category': 'Medical',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'https://www.almightycs.com',
    'license': 'OPL-1',
    "depends": ["acs_hms"], 
    "data": [
        "security/security.xml",
        "views/assets.xml",
        "views/user_dashboard_view.xml",
        "views/user_view.xml",
    ], 
    'images': [
        'static/description/acs_hms_dashboard_almightycs_odoo_cover.gif',
    ],
    'application': False,
    'sequence': 2,
    'price': 75,
    'currency': 'EUR',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
