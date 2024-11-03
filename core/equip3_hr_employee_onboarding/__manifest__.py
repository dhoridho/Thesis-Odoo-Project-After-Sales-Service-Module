# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 HR Employee Onboarding',
    'version': '1.1.10',
    'author': 'Hashmicro / Arivarasan',
    'website': "https://www.hashmicro.com",
    'category': 'Generic Modules/Human Resources',
    'summary': """
    HR Employee Onboarding.
    """,
    'depends': ['base', 'employee_orientation', 'equip3_hr_training', 'equip3_hr_survey_extend', 'oh_employee_documents_expiry'],
    'data': ['security/ir.model.access.csv',
             'security/security.xml',
             'data/sequence.xml',
             'data/mail_template.xml',
             'wizard/hr_launch_plan_wizard.xml',
             'wizard/onboarding_entry_checklist_wizard.xml',
             'wizard/offboarding_exit_checklist_wizard.xml',
             'views/employee_checklists.xml',
             'views/employee_entry_checklist.xml',
             'views/employee_exit_checklist.xml',
             'views/employee_exit_interview.xml',
             'views/employee_offboarding.xml',
             'views/hr_employee.xml',
             'views/employee_onboarding.xml',
             'views/employee_documents.xml',
             ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
