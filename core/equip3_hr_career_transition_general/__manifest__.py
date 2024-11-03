# -*- coding: utf-8 -*-
{
    'name': "equip3_hr_career_transition_general",

    'summary': """""",

    'description': """
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.3',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','equip3_ph_hr_restructure_menu'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/career_transition_general.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
