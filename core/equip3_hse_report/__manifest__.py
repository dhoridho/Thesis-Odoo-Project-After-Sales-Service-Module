# -*- coding: utf-8 -*-
{
    'name': "Equip3 HSE Reports",

    'summary': """
        This module to manage HSE Reports""",

    'description': """
        This module manages HSE features
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Safety Environment',
    'version': '1.1.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'hr', 'equip3_hse_masterdata', 'equip3_hse_operation', 'ks_dashboard_ninja'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/hse_dash.xml',
        'views/incident_report_analysis.xml',
        'views/death_report_analysis.xml',
    ],
}
