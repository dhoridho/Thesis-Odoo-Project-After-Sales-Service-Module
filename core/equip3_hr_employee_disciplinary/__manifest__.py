# -*- coding: utf-8 -*-
{
    'name': "Equip3 HR Employee Disciplinary",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '1.1.15',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','branch','mail','equip3_hr_employee_access_right_setting'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/ir_cron.xml',
        'data/disciplinary_stage_template.xml',
        'data/email.xml',
        'data/attachment.xml',
        'views/hr_employee.xml',
        'views/hr_employee_disciplinary.xml',
        'views/hr_employee_disciplinary_stage.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
