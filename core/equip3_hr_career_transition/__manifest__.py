# -*- coding: utf-8 -*-
{
    'name': "Equip3 HR Career Transition",

    'summary': """
        Manage Career Transition of Employees""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Hashmicro",
    'website': "https://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources/Career Transition',
    'version': '1.2.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'mail', 'equip3_hr_masterdata_employee', 'equip3_hr_contract_extend',
                'equip3_hr_holidays_extend'],

    # always loaded
    'data': [
        'security/career_transition_security.xml',
        'security/ir.model.access.csv',
        'wizard/popup_wizard.xml',
        'data/data.xml',
        'data/transition_category.xml',
        'data/transition_type.xml',
        'report/report.xml',
        'data/ir_sequence.xml',
        'data/mail.xml',
        'data/wa_template.xml',
        'data/cron.xml',
        'views/assets.xml',
        'views/hr_career_transition.xml',
        'views/career_transition_type.xml',
        'views/career_transition_report.xml',
        'views/hr_career_transition_letter.xml',
        'views/hr_career_transition_matrix.xml',
        'views/career_transition_approval_matrix.xml',
        'views/res_config_settings_views.xml',
        'views/career_transition_category.xml',
        'views/hr_career_transition_flow.xml',
        # 'views/templates.xml',
    ],
    'qweb': [
        "static/src/xml/career_transition_flow.xml",
    ],
    # only loaded in demonstration mode
    'installable': True,
    'application': True,
    'auto_install': False,

}
