# -*- coding: utf-8 -*-
{
    'name': "Equip3 HR Employee Access Right Settings",

    'summary': """
        Manage HR Employee Access Right Settings""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Hashmicro",
    'website': "https://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '1.1.23',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','hr','hr_attendance','hr_contract','hr_skills','gamification','hr_holidays','branch','hr_expense','website_slides'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'security/hr_holidays_security.xml',
        'security/hr_expense_security.xml',
        'security/hr_attendance_security.xml',
        'security/training_security.xml',
        'security/travel_security.xml',
        'security/elearning_security.xml',
        'views/hr_employee.xml',
        'views/hr_employee_inherit.xml',
        'views/hr_department.xml',
        'views/hr_contract.xml',
        'views/hr_skills.xml',
        'views/gamification.xml'
        # 'views/hr_employee_inherit.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
