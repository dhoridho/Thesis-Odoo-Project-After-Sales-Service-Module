# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Equip3 Probation Extend',
    'version': '2.1.5',
    'author': 'Hashmicro / Kumar',
    'website': "https://www.hashmicro.com",
    'category': 'Human Resources/Employee Probation',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['dev_employee_probation','equip3_hr_contract_extend'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/sequences.xml',
        'views/probation_period_view.xml',
        'views/employee.xml',
        'views/probation.xml',
        'views/employee_probation_mass.xml',
        'views/hr_contract.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
