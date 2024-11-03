# -*- coding: utf-8 -*-
#################################################################################
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
#################################################################################

{
    'name': 'Geo Location Attendance',
    'version': '1.1.3',
    'summary': 'This module will only allows employee to check in/out within Active Work Location Range.| Geo Attendance | Remote Attendance | Human Resources | Employees | Geo Location | Active Work Location | Attendance Range | Active Location | CheckIn | CheckOut }',
    'description': """This module will get employees Geo Location and only allows them to check in/out within Active Work Location.
    """,
    'category': 'Human Resources/Attendances',
    'license': 'OPL-1',
    'author': 'Kanak Infosystems LLP.',
    'website': 'https://www.kanakinfosystems.com',
    'images': ['static/description/banner.gif'],
    'depends': ['base','hr','base_geolocalize', 'hr_attendance'],
    'data': [
        'views/attendance_location_view.xml',
        # 'views/res_config_settings_views.xml',
        'views/web_asset_backend_template.xml',
        'views/res_partner.xml'
    ],
    'external_dependencies': {
        'python': ['geopy'],
    },
    'sequence': 1,
    'installable': True,
    'auto_install': False,
    'application': False,
    'price': 50,
    'currency': 'EUR',
    'live_test_url': 'https://youtu.be/djwcoX3Lg5w',
}
