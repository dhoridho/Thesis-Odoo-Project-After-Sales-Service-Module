# -*- coding: utf-8 -*-
{
    'name': "equip3_human_resource_restapi",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "PT. Hashmicro Solusi Indonesia",
    'website': "https://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.4.17',

    # any module necessary for this one to work correctly
    'depends': ['base','restapi','web_digital_sign','im_livechat','hr_holidays','equip3_hr_holidays_extend','equip3_hr_training','equip3_hr_elearning_extend','equip3_hr_cash_advance','equip3_hr_setting'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
