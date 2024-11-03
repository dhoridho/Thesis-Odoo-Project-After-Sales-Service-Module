# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 HR Travel Extend',
    'version': '1.2.11',
    'author': 'Hashmicro / Arivarasan',
    'category': 'Human Resources',
    'summary': """
    Cash Advance
    """,
    'depends': ['base', 'bi_employee_travel_managment', 'equip3_accounting_cash_advance', 'equip3_hr_expense_extend',
                'equip3_hr_employee_access_right_setting'],
    'data': [
        'security/ir.model.access.csv',
        'data/scheduler.xml',
        'data/mail.xml',
        'data/wa_template.xml',
        'data/cron.xml',
        'views/hr_travel_extend.xml',
        'views/res_config_settings.xml',
        'views/hr_travel_approval_matrix.xml',
        'views/hr_travel_report.xml',
        'wizard/travel_approve_wizard.xml',
        'views/hr_travel_cancel.xml',
        'wizard/travel_cancel.xml',
        'views/main_menus.xml',
        'views/hr_travel_flow.xml',
        'views/assets.xml',
    ],
    'qweb': [
        "static/src/xml/travel_flow.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
