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
    'name': 'Patient Insurance Management System',
    'summary': 'Patient Insurance Management for Hospital Appointment related Claims',
    'description': """
        Patient Insurance Management for Appointment and related Claims. Hospital Management with Insurance Claim. ACS HMS
    """,
    'category': 'Medical',
    'version': '1.0.11',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'website': 'https://www.almightycs.com',
    'license': 'OPL-1',
    'depends': ['acs_hms', 'acs_hms_document', 'acs_invoice_split'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'report/package_report.xml',
        'report/claim_report.xml',
        'report/claim_sheet_report.xml',
        'views/hms_base_view.xml',
        'views/tpa_view.xml',
        'views/insurance_view.xml',
        'views/claim_view.xml',
        'views/package_view.xml',
        'views/portal_template.xml',
        'views/claim_sheet_view.xml',
        'views/menu_items.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'images': [
        'static/description/hms_insuranceacs_almightycs_odoo_cover.jpg',
    ],
    'installable': True,
    'application': True,
    'sequence': 2,
    'price': 51,
    'currency': 'EUR',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: