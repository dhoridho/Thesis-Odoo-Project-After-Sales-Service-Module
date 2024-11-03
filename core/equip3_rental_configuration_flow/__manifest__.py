# -*- coding: utf-8 -*-
{
    'name': "equip3_rental_configuration_flow",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Hashmicro",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.10',

    # any module necessary for this one to work correctly
    'depends': ['base','equip3_hashmicro_ui', 'equip3_rental_report','equip3_rental_masterdata'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/rental_flow_wizard_views.xml',
        'wizard/assets.xml',
    ],

    'qweb': [
        'static/xml/rental_configuration_flow.xml'
    ],

    'installable': True,
    'application': False,
}
