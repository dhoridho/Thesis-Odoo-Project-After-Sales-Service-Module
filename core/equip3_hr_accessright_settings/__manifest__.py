# -*- coding: utf-8 -*-
{
    'name': "Equip3 HR Access Right Settings",

    'summary': """
        Manage HR Access Right Settings""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Hashmicro",
    'website': "https://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '1.1.2',

    # any module necessary for this one to work correctly
    'depends': ['base','hr_recruitment','hr'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'security/res_groups_hr.xml',
        'security/res_groups.xml',
        # 'security/security.xml',
        # 'views/res_user.xml',
        # 'views/hr_employee.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'installable': True,
    'application': True,
    'auto_install': False,
}
