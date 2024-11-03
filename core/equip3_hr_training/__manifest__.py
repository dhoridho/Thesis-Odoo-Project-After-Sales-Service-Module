# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Equip3 HR Training',
    'version': '1.2.28',
    'author': 'Hashmicro / Kumar',
    'website': "https://www.hashmicro.com",
    'category': 'Training/Training Request',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['base', 'hr', 'survey', 'equip3_hr_survey_extend', 'equip3_hr_employee_access_right_setting',
                'equip3_hr_career_transition',
                # 'equip3_hr_basic_custom_menu'

                ],
    'data': [
        'data/sequence.xml',
        'data/mail_template.xml',
        'data/wa_template_data.xml',
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        # 'security/training_security.xml',
        'data/course_stages.xml',
        'views/training_category.xml',
        'views/job_position.xml',
        'views/training_request.xml',
        'views/training_conduct.xml',
        'views/training_courses.xml',
        'views/training_histories.xml',
        'views/training_stage.xml',
        'views/training_course_stages.xml',
        'views/res_config_settings.xml',
        'views/hr_training_approval_matrix.xml',
        'views/survey_user_input.xml',
        'views/hr_employee.xml',
        'views/training_cancellation.xml',
        'views/training_conduct_cancellation.xml',
        'views/parent_category.xml',
        'views/training_level.xml',
        'wizard/training_approve_wizard.xml',
        'wizard/training_cancellation.xml',
        'views/hr_certificate_template.xml',
        'data/certificate_template.xml',
        'report/certificate.xml',
        'report/training_report.xml',
        'wizard/training_add_employee.xml',
        'views/hr_training_flow.xml',
        'views/main_menus_view.xml',
        'views/assets.xml',
    ],
    'qweb': [
        "static/src/xml/training_flow.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
