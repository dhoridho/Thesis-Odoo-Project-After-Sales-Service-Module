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
    'name': 'Hospitalization',
    'category': 'Medical',
    'summary': 'Manage your Hospital equipment and related process of Inpatient Registration, Surgery, Care, Discharge',
    'description': """
    Hospitalization is include Inpatient Registration, Surgery, Care, Discharge. Hospital related Flows. ACS HMS
    """,
    'version': '1.0.8',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'www.almightycs.com',
    'depends': ['acs_hms', 'acs_hms_surgery'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/transfer_accommodation_view.xml',
        'views/hospitalization_view.xml',
        'views/hospitalization_care_views.xml',
        'views/bed_view.xml',
        'views/ward_view.xml',
        'views/building_view.xml',
        'views/ot_view.xml',
        'views/hms_base_view.xml',
        'views/death_register.xml',
        'views/res_config_settings_views.xml',
        'report/report_hospital_discharge.xml',
        'report/report_visiting_pass.xml',
        'report/report_hospitalization_patient_card.xml',
        'report/ward_patient_list_report.xml',
        'data/sequence.xml',
        'data/hms_data.xml',
        'views/menu_item.xml',
    ],
    'demo': [],
    'images': [
        'static/description/hms_hospitalization_almightycs_odoo_cover.jpg',
    ],
    'sequence': 1,
    'application': True,
    'price': 51,
    'currency': 'EUR',
}