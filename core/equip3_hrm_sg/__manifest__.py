# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Equip3 HRM SG',
    'version': '1.1.1',
    'author': 'Hashmicro / Masbin',
    'website': "https://www.hashmicro.com",
    'category': 'HRM SG',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['base','sg_ow_aw_cpf', 'sg_hr_payslip_YTD', 'l10n_sg_hr_payroll', 'scs_hr_payroll'],
    'data': [

        'views/employee_payslips.xml',
        'data/hr_salary_rule.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
