# -*- coding: utf-8 -*-
{
    'name': "Equip3 HR Overtime Management",

    'summary': """
        To manage overtime rules, overtime request and overtime approval levels""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Hashmicro",
    'website': "https://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources/Attendances',
    'version': '2.3.6',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_attendance','equip3_hr_attendance_extend','equip3_hr_working_schedule','equip3_hr_payroll_extend_id'],

    # always loaded
    'data': [
        'security/hr_attendance_overtime_security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/overtime_rules_data.xml',
        'data/mail.xml',
        'data/wa_template.xml',
        'data/cron.xml',
        'wizard/overtime_approval_wizard.xml',
        'wizard/overtime_actual_approval_wizard.xml',
        'wizard/overtime_actual_convert_leave.xml',
        'wizard/payslip_compute_sheet_wizard.xml',
        'wizard/hr_payroll_payslips_by_employees_views.xml',
        'views/assets.xml',
        'views/overtime_rules.xml',
        'views/resource_calendar.xml',
        'views/overtime_approval_matrix_view.xml',
        'views/overtime_request_view.xml',
        'views/overtime_actual_view.xml',
        'views/res_config_settings_views.xml',
        'views/hr_payslip_views.xml',
        'views/menu.xml',
        'report/hr_overtime_analysis.xml',
        'views/hr_overtime_flow_view.xml',
    ],
    'qweb': [
        "static/src/xml/overtime_flow.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
