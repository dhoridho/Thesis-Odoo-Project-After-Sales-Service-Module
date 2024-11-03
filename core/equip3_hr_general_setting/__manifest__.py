# -*- coding: utf-8 -*-
{
    'name': "equip3_hr_general_setting",

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
    'version': '1.1.2',

    # any module necessary for this one to work correctly
    'depends': ['hr',
                'equip3_hr_attendance_extend',
                'equip3_hr_cash_advance',
                'hr_payroll_community',
                'equip3_hr_holidays_extend',
                'equip3_hr_career_transition',
                'equip3_hr_employee_loan_extend',
                'equip3_hr_training',
                'equip3_hr_travel_extend',
                # 'hr_expense',
                'equip3_hr_expense_extend',
                'website_slides',
                'elearning_external_videos',
                'oh_employee_documents_expiry',
                'equip3_hr_employee_appraisals'
                ],



    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/res_config_settings_view.xml',
        'views/res_config_settings_views_travel.xml',
        'views/res_config_settings_views_attendance.xml',
        'views/res_config_settings_views_cash_advance.xml',
        'views/res_config_settings_views_payroll.xml',
        'views/res_config_settings_views_leave.xml',
        'views/res_config_settings_views_overtime.xml',
        'views/res_config_settings_views_career_transition.xml',
        'views/res_config_settings_views_loan.xml',
        'views/res_config_settings_views_training.xml',
        'views/res_config_settings_views_travel.xml',
        'views/res_config_settings_view_employee_appraisals.xml',
        'views/res_config_settings_view_expenses.xml',
        'views/res_config_settings_views_expenses_extend.xml',
        'views/res_config_settings_view_elearning.xml',
        'views/menu.xml'
        # 'views/res_config_settings_video.xml'
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
