# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 HR Expense Extend',
    'version': '1.4.20',
    'author': 'Hashmicro /Arivarasan',
    'website': "https://www.hashmicro.com",
    'category': 'Expense',
    'summary': """
    HR Years Reimbursement.
    """,
    'depends': ['base', 'hr_expense', 'sale_expense', 'equip3_hr_masterdata_employee', 'equip3_hr_cash_advance', 'app_web_tree_bgcolor', 'equip3_hr_employee_access_right_setting', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/mail.xml',
        'data/cron.xml',
        'wizard/hr_year_reimbursement_wizard_view.xml',
        'wizard/expense_approve_wizard.xml',
        'views/assets.xml',
        'views/hr_year_reimbursement.xml',
        'views/res_config_settings_views.xml',
        'views/hr_expense_approval_matrix.xml',
        'views/hr_expense_sheet.xml',
        'views/hr_expense_flow.xml',
        'views/product_views.xml',
        'data/wa_template.xml',
        'views/hr_expense_menu.xml',
        'views/hr_expense_employee.xml',
        # 'views/hr_expense_limit.xml'
    ],
    'qweb': [
        "static/src/xml/expense_flow.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
