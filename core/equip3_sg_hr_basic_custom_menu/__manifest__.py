# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Equip3 HR Singapore Basic Custom Menu',
    'version': '1.1.3',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'HRM SG',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['base', 'hr', 'hr_timesheet', 'hr_recruitment', 'scs_hr_payroll'],
    'data': [
        'views/human_resource_menu.xml',
        'views/category_menu.xml',
        'security/invisible_menu.xml',
        'views/invisible_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
