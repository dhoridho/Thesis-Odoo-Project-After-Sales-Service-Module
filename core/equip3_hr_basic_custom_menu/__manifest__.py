# -*- coding: utf-8 -*-
{
    'name': "equip3_hr_basic_custom_menu",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.2.2',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'equip3_hr_setting',
                'hr',
                'employee_orientation',
                'equip3_hr_employee_onboarding',
                'hr_holidays',
                'hr_skills',
                'hr_expense',
                'hr_payroll_community',
                'equip3_hr_masterdata_tax_id',
                'equip3_hr_masterdata_employee','sh_hr_dashboard',
                'hr_reward_warning',
                'equip3_accounting_cash_advance',
                'equip3_hr_cash_advance',
                'org_chart_premium','employee_orientation',
                'company_public_holidays_kanak',
                'dev_employee_probation','equip3_hr_employee_disciplinary',
                'oh_employee_documents_expiry','hr_contract_types',
                'equip3_hr_employee_disciplinary',
                'hr_gamification','equip3_hr_working_schedule_calendar',
                'equip3_hr_attendance_extend',
                'hr_attendance_face_recognition',
                'equip3_hr_holidays_extend',
                'equip3_hr_employee_access_right_setting',
                'equip3_hr_attendance_overtime',
                'equip3_hr_employee_loan_extend',
                'equip3_hr_employee_probation',
                'bi_employee_travel_managment',
                'web_editor',
                'website',
                'equip3_hr_training',
                'website_slides',
                'equip3_hr_travel_extend',
                'company_public_holidays_kanak',
                'equip3_hashmicro_ui',
                'equip3_hr_dashboard_extend'
                ],

    # always loaded
    'data': [
        'security/invisible_groups.xml',
        'views/human_resource_menu.xml',
        'views/invisible_menu.xml',
        'views/custom_view_name.xml',
        'views/menu_category.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
