# -*- coding: utf-8 -*-
###############################################################################
# Author      : Kanak Infosystems LLP. (<https://www.kanakinfosystems.com/>)
# Copyright(c): 2012-Present Kanak Infosystems LLP.
# All Rights Reserved.
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://www.kanakinfosystems.com/license>
###############################################################################
{
    'name': 'Company Public Holiday(Global Leaves)',
    'version': '1.1.8',
    'category': 'Human Resources/Time Off',
    'author': 'Kanak Infosystems LLP.',
    'website': 'https://www.kankinfosystems.com',
    'summary': "This odoo module is allow to add company holiday, company can create a public holiday and send holiday list through mail to employees, update calendar and print holiday report. | Public Holiday | Global Leaves | Company Public Holiday | Holiday list | Global Time Off | Calendar | Update Calendar | Time Off | Holiday Report|",
    'description': """
- module allows to add company holiday in Odoo.
===============================================
Key Features:
    * Add company public holiday in odoo.
    * Company holiday list can be send all employee by the email.
    * Holiday list will be automatically update on globel leaves.
    * Holiday list will be automatically update on calendar.

    """,
    'depends': ['base','resource', 'mail', 'hr', 'hr_holidays','equip3_hr_employee_access_right_setting'],
    'data': [
        'data/company_resource_calendar_mail.xml',
        'security/ir.model.access.csv',
        'security/company_public_holidays_rule_security.xml',
        'reports/public_holiday_report_template.xml',
        'views/company_resource_calendar_view.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'sequence': 1,
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 35,
    'currency': 'EUR',
    'live_test_url': 'https://www.youtube.com/watch?v=vx1Vdo6kVTc',
}
