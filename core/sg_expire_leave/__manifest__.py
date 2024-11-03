#  -*- encoding: utf-8 -*-

{
    "name": "Singapore Leaves Expire",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["sg_holiday_extended"],
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "category": "Human Resources",
    "description": """
Singapore Holiday Expire
============================
Added leave expire functionality with leave expire scheduler.
leave allocation with expiry
leave consumption limit
hr leave management
    """,
    'data': ['views/sg_hr_schedular_extended.xml',
             'views/sg_hr_holiday_extended_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 39,
    "currency": 'EUR',
}
