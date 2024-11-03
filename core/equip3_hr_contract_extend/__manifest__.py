# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 HR Contract Extended',
    'author': 'Hashmicro / Kumar',
    'website': "https://www.hashmicro.com",
    'version': '1.2.10',
    'summary': 'Manage your Contract master.',
    'depends': ['hr_contract_types','hr_contract','equip3_hr_employee_access_right_setting'],
    'category': 'Human Resources/Contracts',
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/res_config_settings.xml',
        'views/contract.xml',
        'views/expiry_contract_notification.xml',
        'views/contract_letter.xml',
        'views/to_renew_contract.xml',
        'views/hr_contract.xml',
        'views/salary_increment.xml',
        'views/salary_increment_approval_matrix.xml',
        'report/report.xml',
        'data/data.xml',
        'data/ir_cron.xml',
        'data/contract_letter.xml',
        'data/mail_template.xml',
        'wizard/batch_email.xml',
        'wizard/salary_increment_approval_wizard.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
