# -*- coding: utf-8 -*-
{
    'name': "Equip3 HSE Operation",

    'summary': """
        This module to manage HSE Operation""",

    'description': """
        This module manages HSE features
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Safety Environment',
    'version': '1.1.2',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'utm', 'hr', 'equip3_hr_attendance_extend', 'equip3_hse_accessright_setting', 'equip3_hse_masterdata'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'data/incident_report_employee_seq.xml',
        'views/incident_report_employee.xml',
        'views/multiple_incident_reports.xml',
        'views/action_checklist_view.xml',
        'views/investigation_report_view.xml',
        'views/approval_matrix_action_checklist_view.xml',
        'views/hr_employee_view.xml',
        'views/assets.xml',
        'wizard/reject_approval_matrix_view.xml',
        'wizard/finished_date_view.xml',
    ],
}
