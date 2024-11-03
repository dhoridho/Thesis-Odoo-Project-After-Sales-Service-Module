# -*- coding: utf-8 -*-
{
    'name': "equip3_hr_elearning_extend",

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
    'version': '1.1.13',

    # any module necessary for this one to work correctly
    'depends': ['base', 'equip3_hr_employee_access_right_setting', 'website_slides', 'equip3_hr_training', 'equip3_hr_recruitment_extend', 'equip3_hashmicro_ui', 'website_slides'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/wa_template.xml',
        'views/views.xml',
        'views/assets.xml',
        'views/lms_menu.xml',
        'views/menu_category.xml',
        'views/smart_button.xml',
        'views/hr_elearning_flow.xml',
        'views/website_slides_templates.xml',

    ],
    'qweb': [
        "static/src/xml/elearning_flow.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
