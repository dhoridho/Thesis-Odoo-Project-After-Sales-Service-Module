# -*- coding: utf-8 -*-
{
    'name': "equip3_hr_payroll_general",

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
    'version': '1.1.3',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','hr','equip3_hashmicro_ui','hr_payroll_community'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payslip_period_views.xml',
        'views/hr_payslip.xml',
        'views/hr_salary_rule_views.xml'
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
