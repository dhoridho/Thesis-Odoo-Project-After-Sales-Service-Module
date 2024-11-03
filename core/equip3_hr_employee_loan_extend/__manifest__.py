# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 Employee Loan',
    'version': '1.2.6',
    'author': 'Hashmicro / Arivarasan',
    'category': 'Human Resources/Employees',
    'summary': """
    Employee Loan Details.
    """,
    'depends': ['hr_employee_loan', 'equip3_hr_payroll_extend_id'],
    'data': [
        'data/hr_payroll_data.xml',
        'data/cron.xml',
        'security/loan_security.xml',
        'security/ir.model.access.csv',
        'wizard/loan_approve_wizard.xml',
        'views/assets.xml',
        'views/loan_type.xml',
        'views/hr_employee_loan.xml',
        'views/hr_employee_loan_cancel.xml',
        'views/hr_full_loan_payment.xml',
        'views/hr_loan_approval_matrix.xml',
        'views/res_config_settings.xml',
        'views/loan_write_menu.xml',
        'views/employee_loan_flow.xml',
        'data/loan_sequence.xml',
        'data/mail_data.xml',
        'data/wa_template.xml',
    ],
    'qweb': [
        "static/src/xml/employee_loan_flow.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
