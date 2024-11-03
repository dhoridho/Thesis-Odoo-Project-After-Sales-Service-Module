# -*- coding: utf-8 -*-
# Copyright (C) 2019 Artem Shurshilov <shurshilov.a@yandex.ru>
# License OPL-1.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "hr attendance professional policy technical base ",

    'summary': """
        Module provides quick and effective interaction and inheritance
        for all modules dependent on it, forming one eco system""",

    'author': "Shurshilov Artem",
    'modifier': "Denada/Hashmicro",
    'website': "https://eurhashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Technical Settings',
    'version': '1.1.2',
    "license": "OPL-1",
    'price': 9,
    'currency': 'EUR',
    'images':[
        'static/description/Attendance_base.png',
        'static/description/Attendance_base.png',
        'static/description/Attendance_base.png',
        'static/description/Attendance_base.png',
    ],

    # any module necessary for this one to work correctly
    'depends': ['base','web','hr_attendance'],

    # always loaded
    'data': [
        'views/views.xml',
        # 'security/hr_attendance_security.xml',
    ],

    'qweb': [
        "static/src/xml/base.xml",
    ],
}
