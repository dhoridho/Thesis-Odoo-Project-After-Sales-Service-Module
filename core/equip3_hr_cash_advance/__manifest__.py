# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 HR Cash Advance',
    'version': '1.2.1',
    'author': 'Hashmicro / Arivarasan',
    'category': 'Human Resources/Cash Advance',
    'summary': """
    Set Employee Cash Advance/ Validation.
    """,
    'depends': ['base', 'equip3_accounting_cash_advance', 'equip3_accounting_deposit', 'dev_expense_limit', 'equip3_accounting_accessright_setting', 'equip3_hr_masterdata_employee', 'equip3_hr_recruitment_extend'],
    'data': [
        'security/hr_cash_advance_security.xml',
        'security/ir.model.access.csv',
        'data/mail.xml',
        'views/cash_advance.xml',
        'wizard/wizard.xml',
        'views/res_config_settings_views.xml',
        'views/hr_cash_advance_approval_matrix.xml',
        'views/hr_cash_advance_flow.xml',
        'views/assets.xml',
        'data/ir_sequence.xml',
        'data/wa_template.xml',
        'data/cron.xml',
        'views/hr_cash_advance_report.xml',
        'report/hr_cash_advance_template.xml',
        'views/hr_cash_advance_cycle.xml',
    ],
    'qweb': [
        "static/src/xml/cash_advance_flow.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
