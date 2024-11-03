# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software PVT. LTD.
# See LICENSE file for full copyright & licensing details.

# Author: Aktiv Software PVT. LTD.
# mail:   odoo@aktivsoftware.com
# Copyright (C) 2015-Present Aktiv Software PVT. LTD.
# Contributions:
#           Aktiv Software:
#              - Kinjal Lalani
#              - Surabh Yadav
#              - Tanvi Gajera


{
    'name': 'Multiple Employee Contract',
    'author': 'Aktiv Software',
    'website': 'http://www.aktivsoftware.com',
    'summary': 'Create Multiple Contract at a same time.',
    'description': """This module helps to create multiple employee's
        contracts from a wizard only if the previous contract is
        in expired state.""",
    'license': 'OPL-1',
    'category': 'Generic Modules/Human Resources',
    'version': '14.0.1.0.1',
    'depends': ['hr_payroll_community', 'resource'],
    'data': [
            'security/ir.model.access.csv',
            'wizard/mutli_contract_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'auto_install': False,
    'installable': True,
    'application': True,
}
