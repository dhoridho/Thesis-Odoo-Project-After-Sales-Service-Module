# -*- coding: utf-8 -*-
{
    'name': "Equip3 HSE Masterdata",

    'summary': """
        This module to manage HSE Masterdata""",

    'description': """
        This module manages HSE Masterdata
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Safety Environment',
    'version': '1.1.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'equip3_general_setting'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hse_menuitems.xml',
        'views/incident_category.xml'],
}
