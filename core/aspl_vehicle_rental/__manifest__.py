# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

{
    'name': 'Vehicle Rental System (Community)',
    'category': 'Fleet',
    'summary': 'Book vehicle,service ',
    'description': """You can Manage vehicle rental.""",
    'author': 'Acespritech Solutions Pvt. Ltd.',
    'website': 'http://www.acespritech.com',
    'price': 300.00,
    'currency': 'EUR',
    'depends': ['base', 'fleet', 'hr', 'sale_crm', 'mail', 'account',
                'website_sale'],
    'images': ['static/description/main_screenshot.png'],
    "data": [
        'security/ir.model.access.csv',
        'security/security.xml',
        'report/rental_order.xml',
        'data/data.xml',
        'data/fleet_inspection_data.xml',
        'views/sequence.xml',
        'views/fleet_vehicle_book.xml',
        'views/fleet_vehicle.xml',
        'views/fleet_vehicle_contract.xml',
        'views/fleet_vehicle_station.xml',
        'wizard/fleet_advance_payment_invoice.xml',
        'views/fleet_vehicle_order.xml',
        'views/fleet_vehicle_location.xml',
        'views/fleet_vehicle_operation.xml',
        'views/fleet_vehicle_inspection.xml',
        'views/fleet_vehicle_move.xml',
        'views/fleet_vehicle_inquiry.xml',
        'views/fleet_vehicle_template.xml',
        'views/res_config_settings_view.xml',
        'views/customer_feedback_system_view.xml',
        'views/customer_feedback_template.xml',
        'views/website_menu.xml',
        'views/website_templates.xml',
        'report/rental_order_report.xml',
        'report/rental_contract_report.xml',
        'report/rental_contract_recurring.xml',
        'report/inspection_report.xml',
        'report/inspection_report_template.xml',

    ],
    'qweb': [
        'static/src/xml/vehical_booking_calender.xml',
        'static/src/xml/delivery_sign.xml'],
    'installable': True,
    'auto_install': False,
}
