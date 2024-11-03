# -*- coding: utf-8 -*-
# Copyright (C) 2020 Artem Shurshilov <shurshilov.a@yandex.ru>
# License OPL-1.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "hr attendance face recognition",

    'summary': """
Face recognition check in / out
is a technology capable of identifying or verifying a person
from a digital image or a video frame from a video source""",

    'author': "Shurshilov Artem",
    'modifier': "Denada/Hashmicro",
    'website': "https://eurhashmicro.com",
    # "live_test_url": "https://eurhashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '1.1.4',
    "license": "OPL-1",
    'price': 72,
    'currency': 'EUR',
    'images': [
        'static/description/preview.gif',
        'static/description/face_control.png',
        'static/description/face_control.png',
        'static/description/face_control.png',
    ],

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'hr_attendance_base', 'web_image_webcam', 'field_image_editor'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/views.xml',
        'views/res_users.xml',
        'views/res_config_settings_views.xml',
    ],
    'qweb': [
        "static/src/xml/attendance.xml",
        "static/src/xml/kiosk.xml",
    ],

    "cloc_exclude": [
        "static/src/js/lib/**/*", # exclude a single folder
    ]
}
