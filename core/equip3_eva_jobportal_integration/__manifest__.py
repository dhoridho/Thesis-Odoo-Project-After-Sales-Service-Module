# -*- coding: utf-8 -*-
{
    'name': "equip3_eva_jobportal_integration",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "HashMicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.15',

    # any module necessary for this one to work correctly
    'depends': ['base','hr_recruitment','website_hr_recruitment', 'restapi'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/user_data.xml',
        'views/res_config_settings_view.xml',
        'views/job_category.xml',
        'views/res_partner_industry.xml',
        'views/hr_job.xml',
    ],

}
